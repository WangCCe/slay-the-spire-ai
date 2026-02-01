"""
Action encoder for RL v2 action space (133 actions).
"""

from typing import List, Optional

from spirecomm.communication.action import (
    PlayCardAction,
    PotionAction,
    EndTurnAction,
    ChooseAction,
    ProceedAction,
    LeaveAction,
    ConfirmAction,
    CancelAction,
    CombatRewardAction,
    CardRewardAction,
    RestAction,
)
from spirecomm.spire.screen import ScreenType, RestOption
from spirecomm.spire.game import Game

from . import action_space as space


class ActionEncoderV2:
    MAX_ACTIONS = space.ACTION_DIM

    def encode_play_card(self, card_slot: int, target_index: int) -> int:
        return space.encode_play_card(card_slot, target_index)

    def encode_use_potion(self, potion_slot: int, target_index: int) -> int:
        return space.encode_use_potion(potion_slot, target_index)

    def decode_action(self, action_index: int, game: Game):
        if action_index == space.END_TURN_ACTION:
            return EndTurnAction()

        if space.PLAY_CARD_OFFSET <= action_index < space.USE_POTION_OFFSET:
            offset = action_index - space.PLAY_CARD_OFFSET
            card_slot = offset // space.TARGET_SLOTS
            target_index = offset % space.TARGET_SLOTS
            return PlayCardAction(card_index=card_slot, target_index=self._map_target(game, target_index))

        if space.USE_POTION_OFFSET <= action_index < space.END_TURN_ACTION:
            offset = action_index - space.USE_POTION_OFFSET
            potion_slot = offset // space.TARGET_SLOTS
            target_index = offset % space.TARGET_SLOTS
            return PotionAction(
                use=True,
                potion_index=potion_slot,
                target_index=self._map_target(game, target_index),
            )

        if space.REWARD_OFFSET <= action_index < space.MAP_OFFSET:
            choice_index = action_index - space.REWARD_OFFSET
            screen_type = getattr(game, "screen_type", None)
            if screen_type == ScreenType.COMBAT_REWARD and hasattr(game.screen, "rewards"):
                rewards = game.screen.rewards or []
                if choice_index < len(rewards):
                    return CombatRewardAction(rewards[choice_index])
                return ProceedAction()
            if screen_type == ScreenType.CARD_REWARD and hasattr(game.screen, "cards"):
                cards = game.screen.cards or []
                if choice_index < len(cards):
                    return CardRewardAction(cards[choice_index])
            return ChooseAction(choice_index)

        if space.MAP_OFFSET <= action_index < space.EVENT_OFFSET:
            choice_index = action_index - space.MAP_OFFSET
            return ChooseAction(choice_index)

        if space.EVENT_OFFSET <= action_index < space.SHOP_OFFSET:
            choice_index = action_index - space.EVENT_OFFSET
            return ChooseAction(choice_index)

        if space.SHOP_OFFSET <= action_index < space.REST_OFFSET:
            choice_index = action_index - space.SHOP_OFFSET
            return self._decode_shop_action(choice_index, game)

        if space.REST_OFFSET <= action_index < space.SYSTEM_OFFSET:
            choice_index = action_index - space.REST_OFFSET
            rest_action = self._decode_rest_action(choice_index, game)
            return rest_action if rest_action is not None else ProceedAction()

        if action_index == space.SYSTEM_ACTIONS.confirm:
            return ConfirmAction()
        if action_index == space.SYSTEM_ACTIONS.cancel:
            return CancelAction()
        if action_index == space.SYSTEM_ACTIONS.leave:
            return LeaveAction()
        if action_index == space.SYSTEM_ACTIONS.proceed:
            return ProceedAction()

        raise ValueError(f"Invalid action index: {action_index}")

    def get_action_mask(self, game: Game) -> List[bool]:
        mask = [False] * self.MAX_ACTIONS

        screen_type = getattr(game, "screen_type", None)
        in_combat = getattr(game, "in_combat", False)
        available = set(getattr(game, "available_commands", []) or [])

        if screen_type in (None, ScreenType.NONE) and in_combat:
            self._mask_combat_actions(mask, game)
            self._mask_system_actions(mask, available)
            return mask

        if screen_type in (ScreenType.CARD_REWARD, ScreenType.COMBAT_REWARD, ScreenType.CHEST, ScreenType.BOSS_REWARD):
            self._mask_choice_group(mask, space.REWARD_OFFSET, space.REWARD_COUNT, self._get_choice_count(game))
            self._mask_system_actions(mask, available)
            return mask

        if screen_type == ScreenType.MAP:
            self._mask_choice_group(mask, space.MAP_OFFSET, space.MAP_COUNT, self._get_choice_count(game))
            self._mask_system_actions(mask, available)
            return mask

        if screen_type == ScreenType.EVENT:
            self._mask_choice_group(mask, space.EVENT_OFFSET, space.EVENT_COUNT, self._get_choice_count(game))
            self._mask_system_actions(mask, available)
            return mask

        if screen_type in (ScreenType.SHOP_SCREEN, ScreenType.SHOP_ROOM):
            shop_count = self._get_shop_choice_count(game)
            self._mask_choice_group(mask, space.SHOP_OFFSET, space.SHOP_COUNT, shop_count)
            self._mask_system_actions(mask, available)
            return mask

        if screen_type == ScreenType.REST:
            self._mask_rest_actions(mask, game)
            self._mask_system_actions(mask, available)
            return mask

        if screen_type in (ScreenType.HAND_SELECT, ScreenType.GRID):
            self._mask_choice_group(mask, space.REWARD_OFFSET, space.REWARD_COUNT, self._get_choice_count(game))
            if "confirm" in available:
                mask[space.SYSTEM_ACTIONS.confirm] = True
            if "cancel" in available or "skip" in available or "return" in available:
                mask[space.SYSTEM_ACTIONS.cancel] = True
            return mask

        self._mask_system_actions(mask, available)
        return mask

    def _mask_combat_actions(self, mask: List[bool], game: Game) -> None:
        hand = game.hand or []
        monsters = game.monsters or []
        alive_targets = [
            idx + 1
            for idx, monster in enumerate(monsters[:5])
            if getattr(monster, "current_hp", 0) > 0 and not getattr(monster, "is_gone", False)
        ]

        if getattr(game, "play_available", True):
            for card_idx, card in enumerate(hand[:space.MAX_CARD_SLOTS]):
                if hasattr(card, "is_playable") and not card.is_playable:
                    continue
                if getattr(card, "has_target", False):
                    for target_index in alive_targets:
                        mask[self.encode_play_card(card_idx, target_index)] = True
                else:
                    mask[self.encode_play_card(card_idx, 0)] = True

        for potion_idx, potion in enumerate((game.potions or [])[:space.MAX_POTION_SLOTS]):
            if getattr(potion, "potion_id", None) == "Potion Slot":
                continue
            if hasattr(potion, "can_use") and not potion.can_use:
                continue
            requires_target = getattr(potion, "requires_target", False)
            if requires_target:
                for target_index in alive_targets:
                    mask[self.encode_use_potion(potion_idx, target_index)] = True
            else:
                mask[self.encode_use_potion(potion_idx, 0)] = True

        if getattr(game, "end_available", False):
            mask[space.END_TURN_ACTION] = True

    def _mask_choice_group(self, mask: List[bool], offset: int, capacity: int, count: int) -> None:
        enabled = min(capacity, max(count, 0))
        for idx in range(enabled):
            mask[offset + idx] = True

    def _mask_rest_actions(self, mask: List[bool], game: Game) -> None:
        screen = getattr(game, "screen", None)
        rest_options = getattr(screen, "rest_options", []) if screen else []
        option_to_index = {
            RestOption.REST: 0,
            RestOption.SMITH: 1,
            RestOption.TOKE: 2,
            RestOption.DIG: 3,
            RestOption.LIFT: 4,
            RestOption.RECALL: 5,
        }
        for option in rest_options or []:
            index = option_to_index.get(option)
            if index is not None and index < space.REST_COUNT:
                mask[space.REST_OFFSET + index] = True

    def _mask_system_actions(self, mask: List[bool], available: set) -> None:
        if "confirm" in available:
            mask[space.SYSTEM_ACTIONS.confirm] = True
        if "cancel" in available or "return" in available or "skip" in available:
            mask[space.SYSTEM_ACTIONS.cancel] = True
        if "leave" in available:
            mask[space.SYSTEM_ACTIONS.leave] = True
        if "proceed" in available:
            mask[space.SYSTEM_ACTIONS.proceed] = True

    def _get_choice_count(self, game: Game) -> int:
        if getattr(game, "choice_available", False) and game.choice_list is not None:
            return len(game.choice_list)
        screen = getattr(game, "screen", None)
        if screen is None:
            return 0
        if hasattr(screen, "cards"):
            return len(screen.cards or [])
        if hasattr(screen, "rewards"):
            return len(screen.rewards or [])
        if hasattr(screen, "next_nodes"):
            return len(screen.next_nodes or [])
        return 0

    def _get_shop_choice_count(self, game: Game) -> int:
        if getattr(game, "choice_available", False) and game.choice_list is not None:
            return len(game.choice_list)
        screen = getattr(game, "screen", None)
        if screen is None:
            return 0
        cards = len(getattr(screen, "cards", []) or [])
        relics = len(getattr(screen, "relics", []) or [])
        potions = len(getattr(screen, "potions", []) or [])
        purge = 1 if getattr(screen, "purge_available", False) else 0
        return cards + relics + potions + purge

    def _decode_shop_action(self, choice_index: int, game: Game):
        if getattr(game, "choice_available", False) and game.choice_list is not None:
            return ChooseAction(choice_index)

        screen = getattr(game, "screen", None)
        if screen is None:
            return ChooseAction(choice_index)

        cards = getattr(screen, "cards", []) or []
        relics = getattr(screen, "relics", []) or []
        potions = getattr(screen, "potions", []) or []
        purge_available = getattr(screen, "purge_available", False)

        if choice_index < len(cards):
            from spirecomm.communication.action import BuyCardAction

            return BuyCardAction(cards[choice_index])

        choice_index -= len(cards)
        if choice_index < len(relics):
            from spirecomm.communication.action import BuyRelicAction

            return BuyRelicAction(relics[choice_index])

        choice_index -= len(relics)
        if choice_index < len(potions):
            from spirecomm.communication.action import BuyPotionAction

            return BuyPotionAction(potions[choice_index])

        choice_index -= len(potions)
        if purge_available and choice_index == 0:
            from spirecomm.communication.action import BuyPurgeAction

            return BuyPurgeAction()

        return LeaveAction()

    def _decode_rest_action(self, choice_index: int, game: Game) -> Optional[RestAction]:
        screen = getattr(game, "screen", None)
        rest_options = getattr(screen, "rest_options", []) if screen else []
        index_to_option = {
            0: RestOption.REST,
            1: RestOption.SMITH,
            2: RestOption.TOKE,
            3: RestOption.DIG,
            4: RestOption.LIFT,
            5: RestOption.RECALL,
        }
        option = index_to_option.get(choice_index)
        if option is None or option not in rest_options:
            return None
        return RestAction(option)

    @staticmethod
    def _map_target(game: Game, target_index: int) -> int:
        if target_index <= 0:
            return None
        monsters = game.monsters or []
        if target_index - 1 < len(monsters):
            return target_index - 1
        return None
