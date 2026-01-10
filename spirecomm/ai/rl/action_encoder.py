"""
Action encoder for mapping discrete action indices to Action objects.

Converts between discrete action indices (0-999) and Slay the Spire Action objects.
"""

from typing import List, Optional, Tuple
from spirecomm.spire.game import Game
from spirecomm.communication.action import PlayCardAction, PotionAction, EndTurnAction, ChooseAction, ProceedAction, LeaveAction, ConfirmAction


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

    def __init__(self):
        """Initialize action encoder."""
        pass

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
            # Use named parameters: card_index=X, target_index=Y
            return PlayCardAction(card_index=card_index, target_index=monster_index if monster_index < len(game.monsters) else -1)

        # Use potion
        elif self.USE_POTION_OFFSET <= action_index < self.END_TURN_ACTION:
            offset = action_index - self.USE_POTION_OFFSET
            potion_index = offset // 10
            monster_index = offset % 10
            # Use named parameters to avoid confusion: use=True, potion_index=X, target_index=Y
            return PotionAction(use=True, potion_index=potion_index, target_index=monster_index if monster_index < len(game.monsters) else -1)

        # Card reward selection
        elif self.CARD_REWARD_OFFSET <= action_index < self.MAP_PATH_OFFSET:
            choice_index = action_index - self.CARD_REWARD_OFFSET
            # Clamp to valid range
            if game.choice_list and len(game.choice_list) > 0:
                choice_index = min(choice_index, len(game.choice_list) - 1)
            else:
                choice_index = 0
            return ChooseAction(choice_index)

        # Map path selection
        elif self.MAP_PATH_OFFSET <= action_index < self.EVENT_CHOICE_OFFSET:
            path_index = action_index - self.MAP_PATH_OFFSET
            # Clamp to valid range
            if game.choice_list and len(game.choice_list) > 0:
                path_index = min(path_index, len(game.choice_list) - 1)
            else:
                path_index = 0
            return ChooseAction(path_index)

        # Event choice
        elif self.EVENT_CHOICE_OFFSET <= action_index < self.SHOP_ACTION_OFFSET:
            choice_index = action_index - self.EVENT_CHOICE_OFFSET
            # Clamp to valid range
            if game.choice_list and len(game.choice_list) > 0:
                choice_index = min(choice_index, len(game.choice_list) - 1)
            else:
                choice_index = 0
            return ChooseAction(choice_index)

        # Shop action
        elif self.SHOP_ACTION_OFFSET <= action_index < self.REST_OPTION_OFFSET:
            shop_action = action_index - self.SHOP_ACTION_OFFSET
            # Clamp to valid range for shop
            if game.choice_list and len(game.choice_list) > 0:
                shop_action = min(shop_action, len(game.choice_list) - 1)
            else:
                shop_action = 0
            return ChooseAction(shop_action)

        # Rest site option
        elif self.REST_OPTION_OFFSET <= action_index < self.PROCEED_ACTION:
            rest_option = action_index - self.REST_OPTION_OFFSET
            # Clamp to valid range (typically 4 options: rest, smith, lift, dig)
            if game.choice_list and len(game.choice_list) > 0:
                rest_option = min(rest_option, len(game.choice_list) - 1)
            else:
                rest_option = 0
            return ChooseAction(rest_option)

        # Proceed action (skip/continue button)
        elif action_index == self.PROCEED_ACTION:
            return ProceedAction()

        # Leave action (e.g., leave shop)
        elif action_index == self.LEAVE_ACTION:
            return LeaveAction()

        # Confirm action (e.g., confirm card selection in GRID screen)
        elif action_index == self.CONFIRM_ACTION:
            return ConfirmAction()

        else:
            raise ValueError(f"Invalid action index: {action_index}")

    def get_action_mask(self, game: Game) -> List[bool]:
        """
        Compute boolean mask of valid actions for current game state.

        Args:
            game: Current game state

        Returns:
            Boolean list of length MAX_ACTIONS where True = valid action
        """
        mask = [False] * self.MAX_ACTIONS

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)

        # Game over screen - only proceed is valid
        if "GAME_OVER" in str(game.screen_type):
            mask[self.PROCEED_ACTION] = True
            logger.debug(f"GAME_OVER: Enabled proceed action")
            return mask  # Early return to skip all other logic

        # End turn is only valid in combat when end is available
        if game.in_combat and hasattr(game, 'end_available') and game.end_available:
            mask[self.END_TURN_ACTION] = True

        # Combat actions (only valid when in combat)
        if game.in_combat:
            hand = game.hand if game.hand else []
            monsters = game.monsters if game.monsters else []
            potions = game.potions if game.potions else []

            # Play card actions
            for card_idx in range(min(len(hand), self.MAX_CARDS)):
                for monster_idx in range(len(monsters)):
                    action_idx = self.encode_play_card(card_idx, monster_idx)
                    # Check if card is affordable (cost check)
                    card = hand[card_idx]
                    cost = card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost
                    if game.player and game.player.energy >= cost:
                        mask[action_idx] = True

            # Use potion actions
            for potion_idx in range(min(len(potions), self.MAX_POTIONS)):
                for monster_idx in range(len(monsters)):
                    action_idx = self.encode_use_potion(potion_idx, monster_idx)
                    mask[action_idx] = True

            logger.debug(f"Combat mask: {sum(mask)} valid actions out of {len(mask)}")

        # Card reward screen
        elif game.choice_available and ("card" in str(game.screen_type).lower() or "upgrade" in str(game.screen_type).lower()):
            choices = game.choice_list if game.choice_list else []
            for i in range(len(choices)):
                if i < 10:  # Max 10 choices
                    mask[self.CARD_REWARD_OFFSET + i] = True
            # Fallback: ensure at least one action is valid
            if len(choices) == 0:
                mask[self.CARD_REWARD_OFFSET] = True

        # Combat reward screen (potions/relics after battle)
        elif "COMBAT_REWARD" in str(game.screen_type):
            # Check for potion rewards
            potions = game.potions if game.potions else []
            # Enable use potion actions if potions available
            for potion_idx in range(min(len(potions), self.MAX_POTIONS)):
                # For combat rewards, potions are typically used immediately
                # Use potion at target -1 (no target needed for combat rewards)
                action_idx = self.encode_use_potion(potion_idx, 0)
                mask[action_idx] = True

            # Always enable proceed to skip reward or continue after taking potion
            mask[self.PROCEED_ACTION] = True
            logger.debug(f"COMBAT_REWARD: Enabled {len(potions)} potion actions and proceed")

        # Grid screen (card selection/removal/upgrade)
        elif "GRID" in str(game.screen_type):
            # Grid screens require choose commands
            # choice_list contains available cards/choices
            choices = game.choice_list if game.choice_list else []
            for i in range(len(choices)):
                if i < 10:  # Max 10 choices
                    mask[self.CARD_REWARD_OFFSET + i] = True

            # Always enable confirm action to confirm selection (or skip if nothing selected)
            mask[self.CONFIRM_ACTION] = True

            logger.debug(f"GRID: Enabled {len(choices)} choose actions and confirm")

        # Map screen
        elif "map" in str(game.screen_type).lower():
            # Usually 1-3 path options
            if game.choice_list and len(game.choice_list) > 0:
                for i in range(len(game.choice_list)):
                    if i < 5:
                        mask[self.MAP_PATH_OFFSET + i] = True
            else:
                # Fallback
                mask[self.MAP_PATH_OFFSET] = True

        # Event screen
        elif "event" in str(game.screen_type).lower():
            # Usually 1-3 event choices
            if game.choice_list and len(game.choice_list) > 0:
                for i in range(len(game.choice_list)):
                    if i < 5:
                        mask[self.EVENT_CHOICE_OFFSET + i] = True
            else:
                # Fallback
                mask[self.EVENT_CHOICE_OFFSET] = True

        # Shop screen
        elif "shop" in str(game.screen_type).lower():
            # Shop actions (buy cards, relics, potions, purge)
            if game.choice_list and len(game.choice_list) > 0:
                for i in range(min(len(game.choice_list), 10)):
                    mask[self.SHOP_ACTION_OFFSET + i] = True
            else:
                # Fallback
                for i in range(3):
                    mask[self.SHOP_ACTION_OFFSET + i] = True

            # Always enable leave action to exit shop
            mask[self.LEAVE_ACTION] = True
            logger.debug(f"SHOP: Enabled {len(game.choice_list) if game.choice_list else 0} buy actions and leave")

        # Rest site
        elif "rest" in str(game.screen_type).lower():
            # Rest options: rest, smith, lift, dig
            if game.choice_list and len(game.choice_list) > 0:
                for i in range(len(game.choice_list)):
                    if i < 4:
                        mask[self.REST_OPTION_OFFSET + i] = True
            else:
                # Fallback
                mask[self.REST_OPTION_OFFSET] = True

            # Always enable proceed to confirm rest option choice or skip
            mask[self.PROCEED_ACTION] = True
            logger.debug(f"REST: Enabled {len(game.choice_list) if game.choice_list else 0} rest options and proceed")

        # Ensure at least one action is valid (fallback)
        if not any(mask):
            # If nothing is valid, log warning and enable proceed as safest fallback
            logger.warning(f"No valid actions found! in_combat={game.in_combat}, screen_type={game.screen_type}, choice_available={game.choice_available}")
            # Use PROCEED as safest fallback - works in most contexts
            mask[self.PROCEED_ACTION] = True
            logger.debug(f"Enabled fallback action: PROCEED at index {self.PROCEED_ACTION}")

        logger.debug(f"Final mask: {sum(mask)} valid actions, screen={game.screen_type}")
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
