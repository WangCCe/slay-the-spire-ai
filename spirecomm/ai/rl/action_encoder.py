"""
Action encoder for mapping discrete action indices to Action objects.

Converts between discrete action indices (0-999) and Slay the Spire Action objects.
"""

from typing import List, Optional, Tuple
from spirecomm.spire.game import Game
from spirecomm.communication.action import (
    PlayCardAction,
    PotionAction,
    EndTurnAction,
    ChooseAction,
    ProceedAction,
    LeaveAction,
    ConfirmAction,
    CancelAction,
)


class ActionEncoder:
    """
    Encodes and decodes actions for the RL agent.

    Action space breakdown (1000 total actions):
    - 0-99: Play card 0-9 at monster 0-9
    - 100-119: Use potion 0-9 at monster 0-9
    - 120: End turn
    - 121-130: Card reward selection
    - 131-135: Map path choices
    - 136-140: Event choices
    - 141-150: Shop actions
    - 151-154: Rest site options
    - 155: Proceed (skip/continue button)
    - 156: Leave (e.g., leave shop)
    - 157: Confirm (e.g., confirm card selection in GRID)
    - 158: Cancel (e.g., skip card reward)
    """

    MAX_ACTIONS = 1000
    MAX_CARDS = 10
    MAX_MONSTERS = 10
    MAX_POTIONS = 10

    # Combat actions
    PLAY_CARD_OFFSET = 0
    USE_POTION_OFFSET = 100
    END_TURN_ACTION = 120

    # Non-combat actions
    CARD_REWARD_OFFSET = 121
    MAP_PATH_OFFSET = 131
    EVENT_CHOICE_OFFSET = 136
    SHOP_ACTION_OFFSET = 141
    REST_OPTION_OFFSET = 151
    PROCEED_ACTION = 155
    LEAVE_ACTION = 156
    CONFIRM_ACTION = 157
    CANCEL_ACTION = 158

    def __init__(self):
        """Initialize action encoder."""
        pass

    @staticmethod
    def _is_screen_type(
        game: Game, screen_type: str, case_sensitive: bool = True
    ) -> bool:
        """Check if current screen matches the given type."""
        screen_str = str(game.screen_type)
        if case_sensitive:
            return screen_type in screen_str
        return screen_type.lower() in screen_str.lower()

    @staticmethod
    def _get_clamped_choice_index(action_index: int, offset: int, game: Game) -> int:
        """Clamp choice index to valid range based on available choices."""
        choice_index = action_index - offset
        if game.choice_list and len(game.choice_list) > 0:
            choice_index = min(choice_index, len(game.choice_list) - 1)
        else:
            choice_index = 0
        return choice_index

    def encode_play_card(self, card_index: int, monster_index: int) -> int:
        """
        Encode play card action to action index.

        Args:
            card_index: Index of card in hand (0-9)
            monster_index: Index of monster target (0-9)

        Returns:
            Action index (0-99)
        """
        return self.PLAY_CARD_OFFSET + card_index * 10 + monster_index

    def encode_use_potion(self, potion_index: int, monster_index: int) -> int:
        """
        Encode use potion action to action index.

        Args:
            potion_index: Index of potion (0-9)
            monster_index: Index of monster target (0-9)

        Returns:
            Action index (100-119)
        """
        return self.USE_POTION_OFFSET + potion_index * 10 + monster_index

    def decode_action(self, action_index: int, game: Game) -> Optional[object]:
        """
        Decode action index to Action object.

        Args:
            action_index: Discrete action index (0-999)
            game: Current game state for context

        Returns:
            Action object (PlayCardAction, PotionAction, EndTurnAction, ChooseAction)
        """
        # End turn
        if action_index == self.END_TURN_ACTION:
            return EndTurnAction()

        # Play card
        elif self.PLAY_CARD_OFFSET <= action_index < self.USE_POTION_OFFSET:
            offset = action_index - self.PLAY_CARD_OFFSET
            card_index = offset // 10
            monster_index = offset % 10

            # Determine target index based on card and monster availability
            target_index = None
            if 0 <= card_index < len(game.hand):
                card = game.hand[card_index]
                if hasattr(card, "has_target") and card.has_target:
                    target_index = (
                        monster_index if monster_index < len(game.monsters) else 0
                    )
            # Use named parameters: card_index=X, target_index=Y
            return PlayCardAction(card_index=card_index, target_index=target_index)

        # Use potion
        elif self.USE_POTION_OFFSET <= action_index < self.END_TURN_ACTION:
            offset = action_index - self.USE_POTION_OFFSET
            potion_index = offset // 10
            monster_index = offset % 10
            # Use named parameters to avoid confusion: use=True, potion_index=X, target_index=Y
            return PotionAction(
                use=True,
                potion_index=potion_index,
                target_index=monster_index
                if monster_index < len(game.monsters)
                else -1,
            )

        # Card reward selection
        elif self.CARD_REWARD_OFFSET <= action_index < self.MAP_PATH_OFFSET:
            choice_index = self._get_clamped_choice_index(
                action_index, self.CARD_REWARD_OFFSET, game
            )

            # Special handling for COMBAT_REWARD screen
            # Must use CombatRewardAction(reward_object), not ChooseAction(choice_index)
            if self._is_screen_type(game, "COMBAT_REWARD"):
                from spirecomm.communication.action import CombatRewardAction

                # Get rewards list (try both screen.rewards and choice_list)
                # Chest rewards may use choice_list instead of screen.rewards
                rewards = []
                if hasattr(game.screen, "rewards") and game.screen.rewards:
                    rewards = game.screen.rewards
                elif game.choice_list:
                    rewards = game.choice_list

                if choice_index < len(rewards):
                    return CombatRewardAction(rewards[choice_index])
                else:
                    # Fallback to proceed if invalid index
                    return ProceedAction()

            # Special handling for SHOP_SCREEN
            # Must use BuyCardAction/BuyPotionAction, not ChooseAction
            if self._is_screen_type(game, "SHOP_SCREEN"):
                from spirecomm.communication.action import (
                    BuyCardAction,
                    BuyPotionAction,
                    BuyRelicAction,
                    BuyPurgeAction,
                )
                from spirecomm.spire.screen import RewardType

                screen = game.screen
                if hasattr(screen, "cards") and choice_index < len(screen.cards):
                    # Buying a card
                    return BuyCardAction(screen.cards[choice_index])
                elif hasattr(screen, "potions") and choice_index < len(screen.potions):
                    # Buying a potion
                    return BuyPotionAction(screen.potions[choice_index])
                elif hasattr(screen, "relics") and choice_index < len(screen.relics):
                    # Buying a relic
                    return BuyRelicAction(screen.relics[choice_index])
                else:
                    # Invalid choice, proceed
                    return ProceedAction()

            # Special handling for GRID/HAND_SELECT (choose not supported)
            if self._is_screen_type(game, "GRID"):
                from spirecomm.communication.action import ClickAction, KeyAction

                if "choose" in getattr(game, "available_commands", []):
                    return ChooseAction(choice_index)
                positions = (
                    getattr(game.screen, "card_positions", [])
                    if hasattr(game, "screen")
                    else []
                )
                if positions:
                    return ClickAction(("card", choice_index, 0))
                return KeyAction(f"CARD_{choice_index + 1}")
            if self._is_screen_type(game, "HAND_SELECT"):
                from spirecomm.communication.action import KeyAction

                return KeyAction(f"CARD_{choice_index + 1}")

            # Default: use ChooseAction for other screens
            return ChooseAction(choice_index)

        # Map path selection
        elif self.MAP_PATH_OFFSET <= action_index < self.EVENT_CHOICE_OFFSET:
            path_index = self._get_clamped_choice_index(
                action_index, self.MAP_PATH_OFFSET, game
            )
            return ChooseAction(path_index)

        # Event choice
        elif self.EVENT_CHOICE_OFFSET <= action_index < self.SHOP_ACTION_OFFSET:
            choice_index = self._get_clamped_choice_index(
                action_index, self.EVENT_CHOICE_OFFSET, game
            )
            return ChooseAction(choice_index)

        # Shop action
        elif self.SHOP_ACTION_OFFSET <= action_index < self.REST_OPTION_OFFSET:
            shop_action = self._get_clamped_choice_index(
                action_index, self.SHOP_ACTION_OFFSET, game
            )

            # Special handling for SHOP_SCREEN
            # Must use BuyCardAction/BuyPotionAction/BuyRelicAction, not ChooseAction
            if self._is_screen_type(game, "SHOP_SCREEN"):
                from spirecomm.communication.action import (
                    BuyCardAction,
                    BuyPotionAction,
                    BuyRelicAction,
                    BuyPurgeAction,
                )

                screen = game.screen
                if hasattr(screen, "cards") and shop_action < len(screen.cards):
                    # Buying a card
                    return BuyCardAction(screen.cards[shop_action])
                elif hasattr(screen, "potions") and shop_action < len(screen.potions):
                    # Buying a potion (check if potions exist before cards in shop_action)
                    return BuyPotionAction(
                        screen.potions[shop_action - len(getattr(screen, "cards", []))]
                    )
                elif hasattr(screen, "relics") and shop_action < len(screen.relics):
                    # Buying a relic
                    return BuyRelicAction(screen.relics[shop_action])
                elif hasattr(screen, "purge_available") and screen.purge_available:
                    # Buy purge (card removal)
                    return BuyPurgeAction()
                else:
                    # Invalid choice, leave shop
                    return LeaveAction()

            # Default: use ChooseAction for other screens that use SHOP_ACTION_OFFSET
            return ChooseAction(shop_action)

        # Rest site option
        elif self.REST_OPTION_OFFSET <= action_index < self.PROCEED_ACTION:
            rest_option_index = self._get_clamped_choice_index(
                action_index, self.REST_OPTION_OFFSET, game
            )

            # Must use RestAction(rest_option), not ChooseAction(choice_index)
            # REST screen doesn't accept "choose" command
            if self._is_screen_type(game, "REST"):
                from spirecomm.communication.action import RestAction

                # Get the actual rest options from the screen
                rest_options = (
                    game.screen.rest_options
                    if hasattr(game.screen, "rest_options")
                    else []
                )
                if rest_option_index < len(rest_options):
                    # Use the actual RestOption enum from the screen
                    return RestAction(rest_options[rest_option_index])
                else:
                    # Fallback: if no options or invalid index, just proceed
                    return ProceedAction()
            else:
                # For non-REST screens using this offset (if any)
                return ChooseAction(rest_option_index)

        # Proceed action (skip/continue button)
        elif action_index == self.PROCEED_ACTION:
            return ProceedAction()

        # Leave action (e.g., leave shop)
        elif action_index == self.LEAVE_ACTION:
            return LeaveAction()

        # Confirm action (e.g., confirm card selection in GRID screen)
        elif action_index == self.CONFIRM_ACTION:
            if self._is_screen_type(game, "HAND_SELECT") or self._is_screen_type(
                game, "GRID"
            ):
                return ConfirmAction()
            return ConfirmAction()

        # Cancel action (e.g., skip card reward)
        elif action_index == self.CANCEL_ACTION:
            return CancelAction()

        else:
            raise ValueError(f"Invalid action index: {action_index}")

    def get_action_mask(self, game: Game) -> List[bool]:
        """
        Compute boolean mask of valid actions for current game state.

        IMPORTANT: Screen type checks take priority over in_combat checks.
        Some screens (CARD_REWARD, HAND_SELECT, etc.) can appear during combat
        but only accept specific commands, not combat actions.

        Args:
            game: Current game state

        Returns:
            Boolean list of length MAX_ACTIONS where True = valid action
        """
        mask = [False] * self.MAX_ACTIONS

        # Debug logging
        import logging

        logger = logging.getLogger(__name__)

        # === SCREEN TYPE CHECKS (Priority 1) ===
        # These checks must come BEFORE combat checks, even if in_combat=True

        # Game over screen - only proceed is valid
        if self._is_screen_type(game, "GAME_OVER"):
            mask[self.PROCEED_ACTION] = True
            logger.debug(f"GAME_OVER: Enabled proceed action")
            return mask

        # CHEST screen - open chest
        if self._is_screen_type(game, "CHEST"):
            # Use choose command to open chest
            choices = game.choice_list if game.choice_list else []
            if len(choices) > 0:
                for i in range(min(len(choices), 5)):
                    mask[self.CARD_REWARD_OFFSET + i] = True
            else:
                # Fallback
                mask[self.CARD_REWARD_OFFSET] = True
            logger.debug(f"CHEST: Enabled {len(choices)} choices")
            return mask

        # Card reward screen (including potion-related card selection during combat)
        if game.choice_available and (
            self._is_screen_type(game, "card", case_sensitive=False)
            or self._is_screen_type(game, "upgrade", case_sensitive=False)
        ):
            choices = game.choice_list if game.choice_list else []
            for i in range(len(choices)):
                if i < 10:  # Max 10 choices
                    mask[self.CARD_REWARD_OFFSET + i] = True

            # Enable cancel to skip taking a card
            mask[self.CANCEL_ACTION] = True

            # Fallback: ensure at least one action is valid
            if len(choices) == 0:
                mask[self.CARD_REWARD_OFFSET] = True

            logger.debug(f"CARD_REWARD: Enabled {len(choices)} card choices and cancel")
            return mask

        # HAND_SELECT screen (select cards for effects)
        if self._is_screen_type(game, "HAND_SELECT"):
            if (
                hasattr(game, "screen")
                and hasattr(game.screen, "cards")
                and game.screen.cards
            ):
                choices = game.screen.cards
            else:
                choices = game.choice_list if game.choice_list else []
            for i in range(len(choices)):
                if i < 10:  # Max 10 choices
                    mask[self.CARD_REWARD_OFFSET + i] = True

            selected_cards = (
                getattr(game.screen, "selected_cards", [])
                if hasattr(game, "screen")
                else []
            )
            num_required = (
                getattr(game.screen, "num_cards", 0) if hasattr(game, "screen") else 0
            )
            can_pick_zero = (
                getattr(game.screen, "can_pick_zero", False)
                if hasattr(game, "screen")
                else False
            )
            confirm_ready = can_pick_zero or (
                num_required > 0 and len(selected_cards) >= num_required
            )

            # Allow confirm when selection can be finalized; otherwise allow a state poll.
            if confirm_ready:
                mask[self.CONFIRM_ACTION] = True
            elif len(choices) == 0:
                mask[self.CONFIRM_ACTION] = True

            logger.debug(
                f"HAND_SELECT: Enabled {len(choices)} card choices"
                f"{' and confirm' if confirm_ready else ''}"
            )
            return mask

        # GRID screen (card selection/removal/upgrade)
        if self._is_screen_type(game, "GRID"):
            if (
                hasattr(game, "screen")
                and hasattr(game.screen, "cards")
                and game.screen.cards
            ):
                choices = game.screen.cards
            else:
                choices = game.choice_list if game.choice_list else []
            card_positions = (
                getattr(game.screen, "card_positions", [])
                if hasattr(game, "screen")
                else []
            )
            if not card_positions:
                logger.debug("GRID: No card_positions in screen_state")
            else:
                logger.debug(f"GRID: card_positions count={len(card_positions)}")
            for i in range(len(choices)):
                if i < 10:  # Max 10 choices
                    mask[self.CARD_REWARD_OFFSET + i] = True

            confirm_up = getattr(game.screen, "confirm_up", False)
            if confirm_up or len(choices) == 0:
                mask[self.CONFIRM_ACTION] = True
            logger.debug(
                f"GRID: Enabled {len(choices)} choose actions"
                f"{' and confirm' if confirm_up or len(choices) == 0 else ''}"
            )
            return mask

        # Event screen
        if self._is_screen_type(game, "event", case_sensitive=False):
            if game.choice_list and len(game.choice_list) > 0:
                for i in range(len(game.choice_list)):
                    if i < 5:
                        mask[self.EVENT_CHOICE_OFFSET + i] = True
            else:
                mask[self.EVENT_CHOICE_OFFSET] = True
            logger.debug(
                f"EVENT: Enabled {len(game.choice_list) if game.choice_list else 1} choices"
            )
            return mask

        # MAP screen
        if self._is_screen_type(game, "map", case_sensitive=False):
            if game.choice_list and len(game.choice_list) > 0:
                for i in range(len(game.choice_list)):
                    if i < 5:
                        mask[self.MAP_PATH_OFFSET + i] = True
            else:
                mask[self.MAP_PATH_OFFSET] = True
            logger.debug(
                f"MAP: Enabled {len(game.choice_list) if game.choice_list else 1} paths"
            )
            return mask

        # REST screen
        if self._is_screen_type(game, "rest", case_sensitive=False):
            if game.choice_list and len(game.choice_list) > 0:
                for i in range(len(game.choice_list)):
                    if i < 4:
                        mask[self.REST_OPTION_OFFSET + i] = True
            else:
                mask[self.REST_OPTION_OFFSET] = True
            if game.proceed_available:
                mask[self.PROCEED_ACTION] = True
            logger.debug(
                f"REST: Enabled {len(game.choice_list) if game.choice_list else 1} options"
                f"{' and proceed' if game.proceed_available else ''}"
            )
            return mask

        # SHOP_SCREEN (purchase interface)
        if self._is_screen_type(game, "SHOP_SCREEN"):
            if game.choice_list and len(game.choice_list) > 0:
                for i in range(min(len(game.choice_list), 10)):
                    mask[self.SHOP_ACTION_OFFSET + i] = True
            else:
                for i in range(3):
                    mask[self.SHOP_ACTION_OFFSET + i] = True
            mask[self.LEAVE_ACTION] = True
            logger.debug(
                f"SHOP_SCREEN: Enabled {len(game.choice_list) if game.choice_list else 3} buy actions and leave"
            )
            return mask

        # SHOP_ROOM (entrance - choose to enter or skip)
        if self._is_screen_type(game, "SHOP_ROOM"):
            if game.choice_list and len(game.choice_list) > 0:
                for i in range(min(len(game.choice_list), 5)):
                    mask[self.SHOP_ACTION_OFFSET + i] = True
            mask[self.PROCEED_ACTION] = True
            logger.debug(
                f"SHOP_ROOM: Enabled {len(game.choice_list) if game.choice_list else 0} enter actions and proceed"
            )
            return mask

        # COMBAT_REWARD screen (after battle or chest rewards)
        if self._is_screen_type(game, "COMBAT_REWARD"):
            from spirecomm.spire.screen import RewardType

            rewards = []
            if (
                hasattr(game, "screen")
                and hasattr(game.screen, "rewards")
                and game.screen.rewards
            ):
                rewards = game.screen.rewards
            elif game.choice_list:
                rewards = game.choice_list

            # Enable valid reward choices
            enabled_count = 0
            for i in range(min(len(rewards), 10)):
                reward = rewards[i]

                # Check if this reward is valid
                is_valid = True

                # Check if potion reward and potions are full
                if hasattr(reward, "reward_type"):
                    if reward.reward_type == RewardType.POTION:
                        # Check if player has full potion slots
                        if (
                            hasattr(game, "are_potions_full")
                            and game.are_potions_full()
                        ):
                            is_valid = False
                # Fallback: check if reward has 'potion' attribute (for choice_list rewards)
                elif hasattr(reward, "potion") and reward.potion is not None:
                    if hasattr(game, "are_potions_full") and game.are_potions_full():
                        is_valid = False

                if is_valid:
                    mask[self.CARD_REWARD_OFFSET + i] = True
                    enabled_count += 1

            if game.proceed_available:
                mask[self.PROCEED_ACTION] = True
            if game.cancel_available:
                mask[self.CANCEL_ACTION] = True

            logger.debug(
                f"COMBAT_REWARD: Enabled {enabled_count}/{len(rewards)} reward choices"
                f"{' and proceed' if game.proceed_available else ''}"
                f"{' and cancel' if game.cancel_available else ''}"
            )
            return mask

        # === COMBAT ACTIONS (Priority 2 - only for ScreenType.NONE) ===
        # Only enable combat actions if we haven't matched any special screen type above
        # This prevents combat actions on screens like CARD_REWARD/HAND_SELECT during combat

        if game.in_combat:
            hand = game.hand if game.hand else []
            monsters = game.monsters if game.monsters else []
            potions = game.potions if game.potions else []

            # End turn is only valid when end is available
            if hasattr(game, "end_available") and game.end_available:
                mask[self.END_TURN_ACTION] = True

            # Play card actions (only if card is affordable and playable)
            if getattr(game, "play_available", True):
                for card_idx in range(min(len(hand), self.MAX_CARDS)):
                    card = hand[card_idx]
                    # Check if card is playable (skip curses like Dazed)
                    if hasattr(card, "is_playable") and not card.is_playable:
                        continue
                    cost = card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost
                    if not (game.player and game.player.energy >= cost):
                        continue
                    if hasattr(card, "has_target") and not card.has_target:
                        action_idx = self.encode_play_card(card_idx, 0)
                        mask[action_idx] = True
                    else:
                        for monster_idx, monster in enumerate(monsters):
                            if monster.current_hp <= 0 or monster.is_gone or monster.half_dead:
                                continue
                            action_idx = self.encode_play_card(card_idx, monster_idx)
                            mask[action_idx] = True
                    else:
                        for monster_idx, monster in enumerate(monsters):
                            if (
                                monster.current_hp <= 0
                                or monster.is_gone
                                or monster.half_dead
                            ):
                                continue
                            action_idx = self.encode_play_card(card_idx, monster_idx)
                            mask[action_idx] = True

            # Use potion actions (only if potions are available AND can_use=True)
            for potion_idx in range(min(len(potions), self.MAX_POTIONS)):
                potion = potions[potion_idx]
                # Skip empty potion slots
                if hasattr(potion, "potion_id") and potion.potion_id == "Potion Slot":
                    continue
                # Only enable if potion can be used
                if hasattr(potion, "can_use") and not potion.can_use:
                    continue

                # Enable potion action for each valid target
                for monster_idx, monster in enumerate(monsters):
                    if monster.current_hp <= 0 or monster.is_gone or monster.half_dead:
                        continue
                    action_idx = self.encode_use_potion(potion_idx, monster_idx)
                    mask[action_idx] = True

            logger.debug(f"Combat (ScreenType.NONE): {sum(mask)} valid actions")

        # === FALLBACK ===
        # Ensure at least one action is valid
        if not any(mask):
            logger.warning(
                f"No valid actions found! in_combat={game.in_combat}, screen_type={game.screen_type}"
            )
            mask[self.PROCEED_ACTION] = True
            logger.debug(f"Enabled fallback action: PROCEED")

        logger.debug(
            f"Final mask: {sum(mask)} valid actions, screen={game.screen_type}"
        )
        return mask

    def get_valid_actions(self, game: Game) -> List[int]:
        """
        Get list of valid action indices for current game state.

        Args:
            game: Current game state

        Returns:
            List of valid action indices
        """
        mask = self.get_action_mask(game)
        return [i for i, valid in enumerate(mask) if valid]


# Convenience function
def get_valid_action_mask(game: Game) -> List[bool]:
    """Convenience function to get action mask."""
    encoder = ActionEncoder()
    return encoder.get_action_mask(game)
