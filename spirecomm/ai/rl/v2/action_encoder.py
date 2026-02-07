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
    BuyCardAction,
    BuyRelicAction,
    BuyPotionAction,
    BuyPurgeAction,
    BossRewardAction,
    ChooseMapNodeAction,
    ChooseMapBossAction,
)
from spirecomm.spire.screen import ScreenType, RestOption
from spirecomm.spire.game import Game

from . import action_space as space


class ActionEncoderV2:
    MAX_ACTIONS = space.ACTION_DIM

    def encode_action(self, action, game: Game) -> Optional[int]:
        if action is None:
            return None

        if isinstance(action, EndTurnAction):
            return space.END_TURN_ACTION

        if isinstance(action, PlayCardAction):
            card_index = self._resolve_card_index(game, action)
            if card_index is None or card_index >= space.MAX_CARD_SLOTS:
                return None
            target_slot = self._resolve_target_slot(action)
            return self.encode_play_card(card_index, target_slot)

        if isinstance(action, PotionAction):
            if not getattr(action, "use", False):
                return None
            potion_index = self._resolve_potion_index(game, action)
            if potion_index is None or potion_index >= space.MAX_POTION_SLOTS:
                return None
            target_slot = self._resolve_target_slot(action)
            return self.encode_use_potion(potion_index, target_slot)

        if isinstance(action, (ConfirmAction, CancelAction, LeaveAction, ProceedAction)):
            return self._encode_system_action(action)

        if isinstance(action, RestAction):
            return self._encode_rest_action(action, game)

        if isinstance(action, (BuyCardAction, BuyRelicAction, BuyPotionAction, BuyPurgeAction)):
            return self._encode_shop_action(action, game)

        if isinstance(action, (CombatRewardAction, CardRewardAction, BossRewardAction)):
            return self._encode_reward_action(action, game)

        if isinstance(action, (ChooseMapNodeAction, ChooseMapBossAction)):
            choice_index = self._resolve_map_choice_index(action, game)
            if choice_index is None:
                return None
            return space.MAP_OFFSET + choice_index

        if isinstance(action, ChooseAction):
            return self._encode_choose_action(action, game)

        return None

    def encode_play_card(self, card_slot: int, target_index: int) -> int:
        return space.encode_play_card(card_slot, target_index)

    def encode_use_potion(self, potion_slot: int, target_index: int) -> int:
        return space.encode_use_potion(potion_slot, target_index)

    @staticmethod
    def _has_potion_space(game: Game) -> bool:
        if hasattr(game, "has_potion_space"):
            return game.has_potion_space()
        if hasattr(game, "are_potions_full"):
            return not game.are_potions_full()
        return False

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
            self._mask_choice_group(mask, space.REWARD_OFFSET, space.REWARD_COUNT, self._get_choice_count(game, screen_type))
            self._mask_system_actions(mask, available)
            return mask

        if screen_type == ScreenType.MAP:
            self._mask_choice_group(mask, space.MAP_OFFSET, space.MAP_COUNT, self._get_choice_count(game, screen_type))
            self._mask_system_actions(mask, available)
            return mask

        if screen_type == ScreenType.EVENT:
            self._mask_choice_group(mask, space.EVENT_OFFSET, space.EVENT_COUNT, self._get_choice_count(game, screen_type))
            self._mask_system_actions(mask, available)
            return mask

        if screen_type in (ScreenType.SHOP_SCREEN, ScreenType.SHOP_ROOM):
            self._mask_shop_actions(mask, game)
            self._mask_system_actions(mask, available)
            return mask

        if screen_type == ScreenType.REST:
            self._mask_rest_actions(mask, game)
            self._mask_system_actions(mask, available)
            return mask

        if screen_type in (ScreenType.HAND_SELECT, ScreenType.GRID):
            grid_confirm_up = False
            if screen_type == ScreenType.GRID:
                screen = getattr(game, "screen", None)
                grid_confirm_up = bool(getattr(screen, "confirm_up", False))
            if "choose" in available or getattr(game, "choice_available", False):
                self._mask_choice_group(
                    mask,
                    space.REWARD_OFFSET,
                    space.REWARD_COUNT,
                    self._get_choice_count(game, screen_type),
                )
            if "confirm" in available:
                mask[space.SYSTEM_ACTIONS.confirm] = True
            if not grid_confirm_up and (
                "cancel" in available or "skip" in available or "return" in available
            ):
                mask[space.SYSTEM_ACTIONS.cancel] = True
            return mask

        self._mask_system_actions(mask, available)
        return mask

    def _resolve_card_index(self, game: Game, action: PlayCardAction) -> Optional[int]:
        card_index = getattr(action, "card_index", None)
        if card_index is not None and card_index >= 0:
            return int(card_index)
        card = getattr(action, "card", None)
        if card is None:
            return None
        hand = getattr(game, "hand", []) or []
        card_uuid = getattr(card, "uuid", None)
        if card_uuid is not None:
            for idx, hand_card in enumerate(hand):
                if getattr(hand_card, "uuid", None) == card_uuid:
                    return idx
        try:
            return hand.index(card)
        except Exception:
            return None

    def _resolve_potion_index(self, game: Game, action: PotionAction) -> Optional[int]:
        potion_index = getattr(action, "potion_index", None)
        if potion_index is not None and potion_index >= 0:
            return int(potion_index)
        potion = getattr(action, "potion", None)
        if potion is None:
            return None
        potions = getattr(game, "potions", []) or []
        try:
            return potions.index(potion)
        except Exception:
            return None

    @staticmethod
    def _resolve_target_slot(action) -> int:
        target_index = getattr(action, "target_index", None)
        if target_index is None:
            target_monster = getattr(action, "target_monster", None)
            if target_monster is not None:
                target_index = getattr(target_monster, "monster_index", None)
        if target_index is None:
            return 0
        try:
            target_index = int(target_index)
        except Exception:
            return 0
        if target_index < 0:
            return 0
        return min(space.TARGET_SLOTS - 1, target_index + 1)

    @staticmethod
    def _encode_system_action(action) -> Optional[int]:
        if isinstance(action, ConfirmAction):
            return space.SYSTEM_ACTIONS.confirm
        if isinstance(action, CancelAction):
            return space.SYSTEM_ACTIONS.cancel
        if isinstance(action, LeaveAction):
            return space.SYSTEM_ACTIONS.leave
        if isinstance(action, ProceedAction):
            return space.SYSTEM_ACTIONS.proceed
        return None

    def _encode_choose_action(self, action: ChooseAction, game: Game) -> Optional[int]:
        screen_type = getattr(game, "screen_type", None)
        choice_index = getattr(action, "choice_index", None)
        if choice_index is None:
            choice_index = self._resolve_choice_index(action, game)
        if choice_index is None:
            return None
        try:
            choice_index = int(choice_index)
        except Exception:
            return None

        offset = self._offset_for_screen(screen_type)
        capacity = self._capacity_for_screen(screen_type)
        if offset is None:
            return None
        if choice_index < 0:
            return None
        if capacity is not None and choice_index >= capacity:
            return None
        return offset + choice_index

    def _resolve_choice_index(self, action: ChooseAction, game: Game) -> Optional[int]:
        name = getattr(action, "name", None)
        if name and getattr(game, "choice_list", None):
            try:
                return game.choice_list.index(name)
            except ValueError:
                return None
        screen = getattr(game, "screen", None)
        if screen is None or name is None:
            return None
        if hasattr(screen, "cards"):
            for idx, card in enumerate(screen.cards or []):
                if getattr(card, "name", None) == name:
                    return idx
        if hasattr(screen, "relics"):
            for idx, relic in enumerate(screen.relics or []):
                if getattr(relic, "name", None) == name:
                    return idx
        return None

    @staticmethod
    def _offset_for_screen(screen_type: Optional[ScreenType]) -> Optional[int]:
        if screen_type in (
            ScreenType.CARD_REWARD,
            ScreenType.COMBAT_REWARD,
            ScreenType.CHEST,
            ScreenType.BOSS_REWARD,
        ):
            return space.REWARD_OFFSET
        if screen_type == ScreenType.MAP:
            return space.MAP_OFFSET
        if screen_type == ScreenType.EVENT:
            return space.EVENT_OFFSET
        if screen_type in (ScreenType.SHOP_SCREEN, ScreenType.SHOP_ROOM):
            return space.SHOP_OFFSET
        if screen_type == ScreenType.REST:
            return space.REST_OFFSET
        if screen_type in (ScreenType.HAND_SELECT, ScreenType.GRID):
            return space.REWARD_OFFSET
        return None

    @staticmethod
    def _capacity_for_screen(screen_type: Optional[ScreenType]) -> Optional[int]:
        if screen_type in (
            ScreenType.CARD_REWARD,
            ScreenType.COMBAT_REWARD,
            ScreenType.CHEST,
            ScreenType.BOSS_REWARD,
            ScreenType.HAND_SELECT,
            ScreenType.GRID,
        ):
            return space.REWARD_COUNT
        if screen_type == ScreenType.MAP:
            return space.MAP_COUNT
        if screen_type == ScreenType.EVENT:
            return space.EVENT_COUNT
        if screen_type in (ScreenType.SHOP_SCREEN, ScreenType.SHOP_ROOM):
            return space.SHOP_COUNT
        if screen_type == ScreenType.REST:
            return space.REST_COUNT
        return None

    def _encode_reward_action(self, action, game: Game) -> Optional[int]:
        screen = getattr(game, "screen", None)
        if isinstance(action, CombatRewardAction):
            rewards = getattr(screen, "rewards", None) if screen else None
            if rewards and action.combat_reward in rewards:
                return space.REWARD_OFFSET + rewards.index(action.combat_reward)
        if isinstance(action, CardRewardAction):
            name = getattr(action, "name", None)
            if name and getattr(game, "choice_list", None):
                try:
                    return space.REWARD_OFFSET + game.choice_list.index(name)
                except ValueError:
                    return None
            cards = getattr(screen, "cards", None) if screen else None
            if cards:
                for idx, card in enumerate(cards):
                    if getattr(card, "name", None) == name:
                        return space.REWARD_OFFSET + idx
        if isinstance(action, BossRewardAction):
            name = getattr(action, "name", None)
            relics = getattr(screen, "relics", None) if screen else None
            if relics and name:
                for idx, relic in enumerate(relics):
                    if getattr(relic, "name", None) == name:
                        return space.REWARD_OFFSET + idx
        return self._encode_choose_action(action, game)

    def _encode_shop_action(self, action, game: Game) -> Optional[int]:
        screen = getattr(game, "screen", None)
        if screen is None:
            return self._encode_choose_action(action, game)

        cards = getattr(screen, "cards", []) or []
        relics = getattr(screen, "relics", []) or []
        potions = getattr(screen, "potions", []) or []
        purge_available = getattr(screen, "purge_available", False)

        if isinstance(action, BuyCardAction):
            for idx, card in enumerate(cards):
                if getattr(card, "name", None) == getattr(action, "name", None):
                    return space.SHOP_OFFSET + idx
            return None
        if isinstance(action, BuyRelicAction):
            for idx, relic in enumerate(relics):
                if getattr(relic, "name", None) == getattr(action, "name", None):
                    return space.SHOP_OFFSET + len(cards) + idx
            return None
        if isinstance(action, BuyPotionAction):
            for idx, potion in enumerate(potions):
                if getattr(potion, "name", None) == getattr(action, "name", None):
                    return space.SHOP_OFFSET + len(cards) + len(relics) + idx
            return None
        if isinstance(action, BuyPurgeAction) and purge_available:
            return space.SHOP_OFFSET + len(cards) + len(relics) + len(potions)

        return self._encode_choose_action(action, game)

    def _encode_rest_action(self, action: RestAction, game: Game) -> Optional[int]:
        rest_options = getattr(getattr(game, "screen", None), "rest_options", []) or []
        name = getattr(action, "name", None)
        if name is None:
            return None
        option_map = {
            RestOption.REST.name: 0,
            RestOption.SMITH.name: 1,
            RestOption.TOKE.name: 2,
            RestOption.DIG.name: 3,
            RestOption.LIFT.name: 4,
            RestOption.RECALL.name: 5,
        }
        index = option_map.get(name)
        if index is None:
            return None
        option = RestOption[name] if name in RestOption.__members__ else None
        if option is not None and rest_options and option not in rest_options:
            return None
        return space.REST_OFFSET + index

    def _resolve_map_choice_index(self, action, game: Game) -> Optional[int]:
        if isinstance(action, ChooseMapBossAction):
            choice_list = getattr(game, "choice_list", None) or []
            if "boss" in choice_list:
                return choice_list.index("boss")
            return None
        if isinstance(action, ChooseMapNodeAction):
            nodes = getattr(getattr(game, "screen", None), "next_nodes", None) or []
            if action.node in nodes:
                return nodes.index(action.node)
        return None

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
    def _mask_shop_actions(self, mask: List[bool], game: Game) -> None:
        import logging

        screen_type = getattr(game, "screen_type", None)
        if screen_type == ScreenType.SHOP_ROOM:
            choice_list = getattr(game, "choice_list", None) or []
            if choice_list:
                self._mask_choice_group(mask, space.SHOP_OFFSET, space.SHOP_COUNT, len(choice_list))
                return

        screen = getattr(game, "screen", None)
        if screen is None:
            shop_count = self._get_shop_choice_count(game)
            self._mask_choice_group(mask, space.SHOP_OFFSET, space.SHOP_COUNT, shop_count)
            return

        cards = getattr(screen, "cards", []) or []
        relics = getattr(screen, "relics", []) or []
        potions = getattr(screen, "potions", []) or []
        purge_available = getattr(screen, "purge_available", False)

        index = 0
        for _ in cards:
            if index < space.SHOP_COUNT:
                mask[space.SHOP_OFFSET + index] = True
            index += 1
        for _ in relics:
            if index < space.SHOP_COUNT:
                mask[space.SHOP_OFFSET + index] = True
            index += 1
        has_potion_space = self._has_potion_space(game)
        if has_potion_space:
            for _ in potions:
                if index < space.SHOP_COUNT:
                    mask[space.SHOP_OFFSET + index] = True
                index += 1
        else:
            index += len(potions)
        if purge_available and index < space.SHOP_COUNT:
            mask[space.SHOP_OFFSET + index] = True

        logging.getLogger(__name__).debug(
            "SHOP mask: cards=%s relics=%s potions=%s potion_space=%s purge=%s",
            len(cards),
            len(relics),
            len(potions),
            has_potion_space,
            purge_available,
        )

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

    def _get_choice_count(self, game: Game, screen_type: Optional[ScreenType] = None) -> int:
        if getattr(game, "choice_available", False) and game.choice_list is not None:
            return len(game.choice_list)
        if screen_type in (ScreenType.HAND_SELECT, ScreenType.GRID):
            return 0
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
        screen = getattr(game, "screen", None)
        if screen is not None:
            cards = getattr(screen, "cards", []) or []
            relics = getattr(screen, "relics", []) or []
            potions = getattr(screen, "potions", []) or []
            purge_available = getattr(screen, "purge_available", False)
        else:
            cards = []
            relics = []
            potions = []
            purge_available = False

        if cards or relics or potions or purge_available:
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

                if not self._has_potion_space(game):
                    return LeaveAction()
                return BuyPotionAction(potions[choice_index])

            choice_index -= len(potions)
            if purge_available and choice_index == 0:
                from spirecomm.communication.action import BuyPurgeAction

                return BuyPurgeAction()

            return LeaveAction()

        if getattr(game, "choice_available", False) and game.choice_list is not None:
            if 0 <= choice_index < len(game.choice_list):
                return ChooseAction(choice_index)
            return LeaveAction()

        return ChooseAction(choice_index)

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
