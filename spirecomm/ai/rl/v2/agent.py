"""
RL v2 agent implementation with embedding-based observations.
"""

from dataclasses import dataclass
import logging
import math
import os
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from spirecomm.communication.action import (
    EndTurnAction,
    StartGameAction,
    StateAction,
    WaitAction,
)
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.game import Game
from spirecomm.spire.numeric import coerce_int

from spirecomm.ai.heuristics.card_types import card_type_name
from spirecomm.ai.rl.reward import RewardCalculator
from spirecomm.ai.rl.checkpoint_io import (
    load_torch_checkpoint,
    save_torch_checkpoint,
)

from .action_encoder import ActionEncoderV2
from .action_space import ACTION_DIM, PLAY_CARD_COUNT
from .id_mapping import IdMapper, load_default_id_mapper
from .network import create_dqn_v2
from .replay_buffer import NO_PROPOSED_ACTION, UNKNOWN_PROPOSED_ACTION
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
    anchor_to_executed_action: bool = False
    proposed_action_index: int = UNKNOWN_PROPOSED_ACTION


class RLAgentV2:
    """
    Reinforcement Learning agent using RL v2 action/observation spaces.
    """

    RL_SPACE_VERSION = "v2"
    CHECKPOINT_SCHEMA_VERSION = 2
    CHECKPOINT_REPLAY_LIMIT = 4096

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
        parent_policy_anchor_weight: Optional[float] = None,
        positive_energy_action_imitation_weight: Optional[float] = None,
        positive_energy_parent_end_turn_imitation_weight: Optional[float] = None,
    ):
        self.device = device
        self.training_mode = training
        self.training = training
        self.epsilon = epsilon
        self.network_type = network_type
        self.chosen_class = PlayerClass.IRONCLAD
        if parent_policy_anchor_weight is None:
            parent_policy_anchor_weight = float(
                os.environ.get("STS_RL_PARENT_POLICY_ANCHOR_WEIGHT", "0")
            )
        if (
            not math.isfinite(parent_policy_anchor_weight)
            or parent_policy_anchor_weight < 0.0
        ):
            raise ValueError(
                "parent policy anchor weight must be finite and non-negative"
            )
        if parent_policy_anchor_weight > 0.0 and (not training or not model_path):
            raise ValueError(
                "positive parent policy anchor weight requires RL v2 training "
                "with a parent checkpoint"
            )
        self.parent_policy_anchor_weight = float(parent_policy_anchor_weight)
        if positive_energy_action_imitation_weight is None:
            positive_energy_action_imitation_weight = float(
                os.environ.get(
                    "STS_RL_POSITIVE_ENERGY_ACTION_IMITATION_WEIGHT", "0"
                )
            )
        if (
            not math.isfinite(positive_energy_action_imitation_weight)
            or positive_energy_action_imitation_weight < 0.0
        ):
            raise ValueError(
                "positive energy action imitation weight must be finite and non-negative"
            )
        if positive_energy_action_imitation_weight > 0.0 and not training:
            raise ValueError(
                "positive energy action imitation weight requires RL v2 training"
            )
        self.positive_energy_action_imitation_weight = float(
            positive_energy_action_imitation_weight
        )
        if positive_energy_parent_end_turn_imitation_weight is None:
            positive_energy_parent_end_turn_imitation_weight = float(
                os.environ.get(
                    "STS_RL_POSITIVE_ENERGY_PARENT_END_TURN_IMITATION_WEIGHT", "0"
                )
            )
        if (
            not math.isfinite(positive_energy_parent_end_turn_imitation_weight)
            or positive_energy_parent_end_turn_imitation_weight < 0.0
        ):
            raise ValueError(
                "positive energy parent-EndTurn imitation weight must be "
                "finite and non-negative"
            )
        if positive_energy_parent_end_turn_imitation_weight > 0.0 and not training:
            raise ValueError(
                "positive energy parent-EndTurn imitation weight requires RL v2 training"
            )
        if (
            positive_energy_parent_end_turn_imitation_weight > 0.0
            and self.parent_policy_anchor_weight <= 0.0
        ):
            raise ValueError(
                "positive energy parent-EndTurn imitation requires a parent policy anchor"
            )
        if (
            positive_energy_parent_end_turn_imitation_weight > 0.0
            and self.positive_energy_action_imitation_weight > 0.0
        ):
            raise ValueError("positive-energy imitation objectives are mutually exclusive")
        self.positive_energy_parent_end_turn_imitation_weight = float(
            positive_energy_parent_end_turn_imitation_weight
        )

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
                parent_policy_anchor_weight=self.parent_policy_anchor_weight,
                positive_energy_action_imitation_weight=(
                    self.positive_energy_action_imitation_weight
                ),
                positive_energy_parent_end_turn_imitation_weight=(
                    self.positive_energy_parent_end_turn_imitation_weight
                ),
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

        boss_min_epsilon = float(
            os.environ.get("STS_RL_BOSS_MIN_EPSILON", "0.3")
        )
        if not math.isfinite(boss_min_epsilon) or not 0.0 <= boss_min_epsilon <= 1.0:
            raise ValueError("boss minimum epsilon must be finite and within [0, 1]")
        self.boss_min_epsilon = boss_min_epsilon
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
        logger.info(
            "RLAgentV2 parent policy anchor config: weight=%.6f",
            self.parent_policy_anchor_weight,
        )
        logger.info(
            "RLAgentV2 positive-energy action imitation config: weight=%.6f",
            self.positive_energy_action_imitation_weight,
        )
        logger.info(
            "RLAgentV2 positive-energy parent-EndTurn imitation config: weight=%.6f",
            self.positive_energy_parent_end_turn_imitation_weight,
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

        self.latent_gated_shadow = None
        self.latent_gated_candidate = None
        shadow_registration = os.environ.get(
            "STS_COMBAT_RL_LATENT_SHADOW_REGISTRATION", ""
        ).strip()
        candidate_registration = os.environ.get(
            "STS_COMBAT_RL_LATENT_CANDIDATE_REGISTRATION", ""
        ).strip()
        if shadow_registration and candidate_registration:
            raise ValueError(
                "latent-gated shadow and candidate registrations are mutually exclusive"
            )
        if model_path:
            self.load_model(model_path)
        if shadow_registration:
            from .latent_gated_live_shadow import (
                initialize_latent_gated_live_shadow,
            )

            adapter_metadata = self._build_metadata().as_dict()
            adapter_metadata.pop("rl_space_version")
            self.latent_gated_shadow = initialize_latent_gated_live_shadow(
                parent=self.network,
                metadata=adapter_metadata,
                model_path=model_path,
                training=self.training_mode,
                epsilon=self.epsilon,
                expert_mix_enabled=self.expert_mix_enabled,
                repo_root=Path(__file__).resolve().parents[4],
                device=self.device,
            )
        if candidate_registration:
            from .latent_gated_live_candidate import (
                initialize_latent_gated_live_candidate,
            )

            adapter_metadata = self._build_metadata().as_dict()
            adapter_metadata.pop("rl_space_version")
            self.latent_gated_candidate = initialize_latent_gated_live_candidate(
                parent=self.network,
                metadata=adapter_metadata,
                model_path=model_path,
                training=self.training_mode,
                epsilon=self.epsilon,
                expert_mix_enabled=self.expert_mix_enabled,
                repo_root=Path(__file__).resolve().parents[4],
                device=self.device,
            )

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

            parent_action_index = action_index
            candidate = getattr(self, "latent_gated_candidate", None)
            if candidate is not None and candidate.enabled:
                try:
                    action_index = candidate.select_action(
                        game=game,
                        continuous=encoded.continuous,
                        card_ids=encoded.card_ids,
                        potion_ids=encoded.potion_ids,
                        relic_ids=encoded.relic_ids,
                        action_mask=action_mask,
                        parent_action_index=parent_action_index,
                    )
                except Exception as candidate_error:
                    logger.error(
                        "RLAgentV2 latent-gated candidate proposal failed: %s",
                        candidate_error,
                    )
                    candidate.record_runtime_error(
                        stage="proposal", error=candidate_error, game=game
                    )
                    action_index = parent_action_index

            action = self.action_encoder.decode_action(action_index, game)

            shadow = getattr(self, "latent_gated_shadow", None)
            if shadow is not None and shadow.enabled:
                try:
                    shadow.observe_proposal(
                        game=game,
                        continuous=encoded.continuous,
                        card_ids=encoded.card_ids,
                        potion_ids=encoded.potion_ids,
                        relic_ids=encoded.relic_ids,
                        action_mask=action_mask,
                        parent_action_index=parent_action_index,
                    )
                except Exception as shadow_error:
                    logger.error(
                        "RLAgentV2 latent-gated shadow proposal failed: %s",
                        shadow_error,
                    )
                    shadow.record_runtime_error(
                        stage="proposal", error=shadow_error, game=game
                    )

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
        self.observe_next_state(
            game,
            encoded=encoded,
            action_mask=action_mask,
        )

        self.pending_transition = PendingTransition(
            continuous=encoded.continuous,
            card_ids=encoded.card_ids,
            potion_ids=encoded.potion_ids,
            relic_ids=encoded.relic_ids,
            action_index=action_index,
            action_mask=action_mask,
            game=game,
            proposed_action_index=action_index,
        )

    def observe_next_state(
        self,
        game: Game,
        *,
        terminal: bool = False,
        encoded=None,
        action_mask: Optional[np.ndarray] = None,
    ) -> Optional[float]:
        """Finish the pending transition against the next observed game state."""
        if not self.training_mode or self.trainer is None or self.pending_transition is None:
            return None

        pending = self.pending_transition
        reward_info = {}
        action_context = self._build_action_context(pending)
        reward = self.reward_calculator.calculate_step_reward(
            current_game=game,
            last_game=pending.game,
            action_type="combat",
            debug_info=reward_info,
            action_context=action_context,
        )
        crossed_floor_boundary = self._crossed_floor_boundary(pending.game, game)
        done = bool(terminal or self._is_terminal(game) or crossed_floor_boundary)
        if crossed_floor_boundary and not terminal and not self._is_terminal(game):
            logger.info(
                "RLAgentV2 terminalized pending transition across floor boundary: %s -> %s",
                getattr(pending.game, "floor", None),
                getattr(game, "floor", None),
            )

        if done:
            next_continuous = None
            next_card_ids = None
            next_potion_ids = None
            next_relic_ids = None
            next_action_mask = np.zeros(self.action_encoder.MAX_ACTIONS, dtype=bool)
        else:
            if encoded is None:
                encoded = self.state_encoder.encode(game)
            if action_mask is None:
                action_mask = np.array(
                    self.action_encoder.get_action_mask(game),
                    dtype=bool,
                )
            next_continuous = encoded.continuous
            next_card_ids = encoded.card_ids
            next_potion_ids = encoded.potion_ids
            next_relic_ids = encoded.relic_ids
            next_action_mask = action_mask

        accepted = self.trainer.store_transition(
            continuous=pending.continuous,
            card_ids=pending.card_ids,
            potion_ids=pending.potion_ids,
            relic_ids=pending.relic_ids,
            action=pending.action_index,
            reward=reward,
            next_continuous=next_continuous,
            next_card_ids=next_card_ids,
            next_potion_ids=next_potion_ids,
            next_relic_ids=next_relic_ids,
            done=done,
            action_mask=pending.action_mask,
            next_action_mask=next_action_mask,
            anchor_to_executed_action=pending.anchor_to_executed_action,
            proposed_action_index=pending.proposed_action_index,
        )
        self.pending_transition = None
        if accepted is False:
            logger.warning("Replay rejected a pending RL transition")
            return None
        self.episode_reward += reward
        self.episode_steps += 1
        return self.trainer.train_step()

    def commit_executed_action(self, game: Game, action) -> bool:
        """Bind replay attribution to the action emitted after outer safety guards."""
        candidate = getattr(self, "latent_gated_candidate", None)
        shadow = getattr(self, "latent_gated_shadow", None)
        live_runtime = candidate if candidate is not None else shadow
        runtime_label = "candidate" if candidate is not None else "shadow"
        if live_runtime is not None and live_runtime.pending is not None:
            try:
                if isinstance(action, WaitAction):
                    live_runtime.discard_transient_action(reason="wait_action")
                else:
                    executed_live_index = self.action_encoder.encode_action(
                        action, game
                    )
                    live_runtime.commit_executed_action(
                        game=game,
                        executed_action_index=executed_live_index,
                    )
            except Exception as live_error:
                logger.error(
                    "RLAgentV2 latent-gated %s commit failed: %s",
                    runtime_label,
                    live_error,
                )
                live_runtime.record_runtime_error(
                    stage="commit", error=live_error, game=game
                )
        if not self.training_mode or self.trainer is None:
            return False

        same_state_pending = (
            self.pending_transition is not None
            and self.pending_transition.game is game
        )
        action_index = self.action_encoder.encode_action(action, game)
        if not getattr(game, "in_combat", False) or action_index is None:
            if same_state_pending:
                self.pending_transition = None
            return False

        action_mask = np.array(
            self.action_encoder.get_action_mask(game),
            dtype=bool,
        )
        if (
            action_index < 0
            or action_index >= len(action_mask)
            or not action_mask[action_index]
        ):
            if same_state_pending:
                self.pending_transition = None
            logger.warning(
                "Executed combat action is outside the current RL mask; transition discarded: %s",
                type(action).__name__,
            )
            return False

        if same_state_pending:
            proposed_action_index = self.pending_transition.proposed_action_index
            if proposed_action_index == UNKNOWN_PROPOSED_ACTION:
                proposed_action_index = self.pending_transition.action_index
                self.pending_transition.proposed_action_index = proposed_action_index
            self.pending_transition.action_index = action_index
            self.pending_transition.action_mask = action_mask
            self.pending_transition.anchor_to_executed_action = bool(
                self.pending_transition.anchor_to_executed_action
                or action_index != proposed_action_index
            )
            return True

        if self.pending_transition is not None:
            logger.warning("Pending transition was not observed before a new emitted action")
            return False

        encoded = self.state_encoder.encode(game)
        self.pending_transition = PendingTransition(
            continuous=encoded.continuous,
            card_ids=encoded.card_ids,
            potion_ids=encoded.potion_ids,
            relic_ids=encoded.relic_ids,
            action_index=action_index,
            action_mask=action_mask,
            game=game,
            anchor_to_executed_action=True,
            proposed_action_index=NO_PROPOSED_ACTION,
        )
        return True

    def finalize_training_episode(self, game: Game) -> Optional[float]:
        if game is None:
            return None
        result = self.observe_next_state(game, terminal=True)
        if self.trainer is not None:
            self.trainer.update_episode_count()
        return result

    def discard_pending_transition(self) -> None:
        self.pending_transition = None

    def abort_training_episode(self) -> None:
        self.discard_pending_transition()

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
            expert_card = getattr(expert_action, "card", None)
            target_monster = getattr(expert_action, "target_monster", None)
            logger.info(
                "Expert action masked out: index=%s action=%s card_index=%s "
                "card_id=%s card_uuid=%s target_index=%s target_monster_index=%s",
                expert_index,
                type(expert_action).__name__ if expert_action is not None else "None",
                getattr(expert_action, "card_index", None),
                getattr(expert_card, "card_id", None),
                getattr(expert_card, "uuid", None),
                getattr(expert_action, "target_index", None),
                getattr(target_monster, "monster_index", None),
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
    def _crossed_floor_boundary(previous_game: Game, current_game: Game) -> bool:
        previous_floor = getattr(previous_game, "floor", None)
        current_floor = getattr(current_game, "floor", None)
        if previous_floor is None or current_floor is None:
            return False
        try:
            return int(previous_floor) != int(current_floor)
        except (TypeError, ValueError, OverflowError):
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
        for live_runtime in (
            getattr(self, "latent_gated_candidate", None),
            getattr(self, "latent_gated_shadow", None),
        ):
            if live_runtime is not None:
                live_runtime.discard_pending()
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
            schema_version = int(checkpoint.get("checkpoint_schema_version", 1))
            if schema_version > self.CHECKPOINT_SCHEMA_VERSION:
                raise ValueError(
                    f"Unsupported checkpoint schema {schema_version}: {model_path}"
                )
            checkpoint_kind = checkpoint.get(
                "checkpoint_kind", "legacy" if schema_version == 1 else None
            )
            target_state = checkpoint.get("target_network_state_dict")
            replay_state_present = "replay_buffer_state_dict" in checkpoint
            replay_state = checkpoint.get("replay_buffer_state_dict")
            if schema_version == self.CHECKPOINT_SCHEMA_VERSION and checkpoint_kind == "training":
                required_fields = {
                    "episode",
                    "epsilon",
                    "learning_starts",
                    "optimizer_state_dict",
                    "total_steps",
                }
                missing_fields = sorted(required_fields.difference(checkpoint))
                if target_state is None or not replay_state_present or missing_fields:
                    raise ValueError(
                        f"Checkpoint schema {schema_version} missing training state "
                        f"{missing_fields}: {model_path}"
                    )
                learning_starts = int(checkpoint["learning_starts"])
                if not (
                    self.trainer.batch_size
                    <= learning_starts
                    <= self.trainer.replay_buffer.buffer_size
                ):
                    raise ValueError(
                        f"Checkpoint learning_starts out of range: {learning_starts}"
                    )
                self.trainer.target_network.load_state_dict(target_state)
                self.trainer.replay_buffer.load_state_dict(replay_state)
                self.trainer.learning_starts = learning_starts
            elif checkpoint_kind in {"legacy", "weights"}:
                self.trainer.target_network.load_state_dict(state_dict)
                self.trainer.replay_buffer.clear()
                self.trainer.learning_starts = max(
                    self.trainer.learning_starts,
                    self.CHECKPOINT_REPLAY_LIMIT,
                )
                logger.warning(
                    "%s v2 checkpoint has no replay/target continuation state; "
                    "require %s replay transitions before learning resumes",
                    checkpoint_kind.capitalize(),
                    self.trainer.learning_starts,
                )
            else:
                raise ValueError(
                    f"Unsupported checkpoint kind {checkpoint_kind!r} for schema "
                    f"{schema_version}: {model_path}"
                )
            optimizer_state = checkpoint.get("optimizer_state_dict")
            if optimizer_state is not None:
                self.trainer.optimizer.load_state_dict(optimizer_state)
            self.trainer.epsilon = checkpoint.get("epsilon", self.trainer.epsilon)
            self.trainer.total_steps = checkpoint.get("total_steps", self.trainer.total_steps)
            self.trainer.episode_count = int(
                checkpoint.get("episode", self.trainer.episode_count)
            )
            if self.trainer.parent_policy_anchor_weight > 0.0:
                anchor_state = checkpoint.get("parent_policy_anchor_state_dict")
                stored_weight = checkpoint.get("parent_policy_anchor_weight")
                if anchor_state is not None:
                    if stored_weight is None or not math.isclose(
                        float(stored_weight),
                        self.trainer.parent_policy_anchor_weight,
                    ):
                        raise ValueError(
                            "anchored checkpoint weight does not match requested "
                            "parent policy anchor weight"
                        )
                else:
                    anchor_state = state_dict
                self.trainer.set_parent_policy_anchor(anchor_state)
                logger.info(
                    "Loaded frozen parent policy anchor from %s",
                    "checkpoint anchor state"
                    if checkpoint.get("parent_policy_anchor_state_dict") is not None
                    else "starting checkpoint online policy",
                )
            stored_imitation_weight = checkpoint.get(
                "positive_energy_action_imitation_weight"
            )
            if stored_imitation_weight is not None and not math.isclose(
                float(stored_imitation_weight),
                self.trainer.positive_energy_action_imitation_weight,
            ):
                raise ValueError(
                    "checkpoint positive energy action imitation weight does not "
                    "match requested weight"
                )
            stored_parent_end_turn_imitation_weight = checkpoint.get(
                "positive_energy_parent_end_turn_imitation_weight"
            )
            if (
                stored_parent_end_turn_imitation_weight is not None
                and not math.isclose(
                    float(stored_parent_end_turn_imitation_weight),
                    self.trainer.positive_energy_parent_end_turn_imitation_weight,
                )
            ):
                raise ValueError(
                    "checkpoint positive energy parent-EndTurn imitation weight "
                    "does not match requested weight"
                )
            logger.info("Loaded v2 trainer checkpoint from %s", model_path)
        else:
            self.network.load_state_dict(state_dict)
            self.network.eval()
            logger.info("Loaded v2 model weights from %s", model_path)

    def save_model(self, model_path: str, episode: int = 0) -> None:
        metadata = self._build_metadata()
        checkpoint = {
            "checkpoint_schema_version": self.CHECKPOINT_SCHEMA_VERSION,
            "checkpoint_kind": "training" if self.training_mode else "weights",
            "metadata": metadata.as_dict(),
            "rl_space_version": metadata.rl_space_version,
            "online_network_state_dict": self.network.state_dict(),
            "episode": episode,
        }

        if self.training_mode and self.trainer is not None:
            checkpoint["episode"] = self.trainer.episode_count
            checkpoint.update(
                {
                    "target_network_state_dict": self.trainer.target_network.state_dict(),
                    "replay_buffer_state_dict": self.trainer.replay_buffer.state_dict(
                        max_transitions=self.CHECKPOINT_REPLAY_LIMIT
                    ),
                    "optimizer_state_dict": self.trainer.optimizer.state_dict(),
                    "epsilon": self.trainer.epsilon,
                    "learning_starts": self.trainer.learning_starts,
                    "total_steps": self.trainer.total_steps,
                    "positive_energy_action_imitation_weight": (
                        self.trainer.positive_energy_action_imitation_weight
                    ),
                    "positive_energy_parent_end_turn_imitation_weight": (
                        self.trainer.positive_energy_parent_end_turn_imitation_weight
                    ),
                    "training_metrics": {
                        "last_total_loss": self.trainer.last_loss,
                        "last_td_loss": self.trainer.last_td_loss,
                        "last_parent_policy_anchor_loss": (
                            self.trainer.last_parent_policy_anchor_loss
                        ),
                        "last_positive_energy_action_imitation_loss": (
                            self.trainer.last_positive_energy_action_imitation_loss
                        ),
                        "last_positive_energy_action_imitation_count": (
                            self.trainer.last_positive_energy_action_imitation_count
                        ),
                        "last_positive_energy_parent_end_turn_imitation_loss": (
                            self.trainer.last_positive_energy_parent_end_turn_imitation_loss
                        ),
                        "last_positive_energy_parent_end_turn_imitation_count": (
                            self.trainer.last_positive_energy_parent_end_turn_imitation_count
                        ),
                    },
                }
            )
            if self.trainer.parent_policy_anchor_network is not None:
                checkpoint.update(
                    {
                        "parent_policy_anchor_weight": self.trainer.parent_policy_anchor_weight,
                        "parent_policy_anchor_state_dict": self.trainer.parent_policy_anchor_network.state_dict(),
                    }
                )

        save_torch_checkpoint(checkpoint, model_path)
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
    parent_policy_anchor_weight: Optional[float] = None,
    positive_energy_action_imitation_weight: Optional[float] = None,
    positive_energy_parent_end_turn_imitation_weight: Optional[float] = None,
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
        parent_policy_anchor_weight=parent_policy_anchor_weight,
        positive_energy_action_imitation_weight=(
            positive_energy_action_imitation_weight
        ),
        positive_energy_parent_end_turn_imitation_weight=(
            positive_energy_parent_end_turn_imitation_weight
        ),
    )
