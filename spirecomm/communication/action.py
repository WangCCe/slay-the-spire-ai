import time

from spirecomm.spire.screen import ScreenType, reward_type_name


def _has_potion_space(game_state):
    has_potion_space = getattr(game_state, "has_potion_space", None)
    if callable(has_potion_space):
        try:
            return bool(has_potion_space())
        except Exception:
            pass

    are_potions_full = getattr(game_state, "are_potions_full", None)
    if callable(are_potions_full):
        return not bool(are_potions_full())

    return True


class Action:
    """A base class for an action to take in Slay the Spire"""

    def __init__(self, command="state", requires_game_ready=True):
        self.command = command
        self.requires_game_ready = requires_game_ready

    def can_be_executed(self, coordinator):
        """Indicates whether the given action can currently be executed, given the coordinator's state

        :param coordinator: The coordinator which will be used to execute the action
        :return: True if the action can currently be executed
        ":rtype: boolean
        """
        if self.requires_game_ready:
            return coordinator.game_is_ready
        else:
            return True

    def execute(self, coordinator):
        """Given the coordinator's current state, execute the given action

        :param coordinator: The coordinator which will be used to execute the action
        :return: None
        """
        coordinator.send_message(self.command)


class PlayCardAction(Action):
    """An action to play a specified card from your hand"""

    def __init__(
        self, card=None, card_index=-1, target_monster=None, target_index=None
    ):
        super().__init__("play")
        self.card = card
        self.card_index = card_index
        self.target_index = target_index
        self.target_monster = target_monster

    def execute(self, coordinator):
        if self.card is not None:
            card_uuid = getattr(self.card, "uuid", None)
            if card_uuid is not None:
                for idx, hand_card in enumerate(coordinator.last_game_state.hand):
                    if getattr(hand_card, "uuid", None) == card_uuid:
                        self.card = hand_card
                        self.card_index = idx
                        break
                else:
                    raise Exception("Specified card for CardAction is not in hand")
            else:
                # If card doesn't have uuid, try to use card_index if provided
                if self.card_index >= 0:
                    # card_index is already set, use it
                    pass
                else:
                    # Try to find card in hand (may fail if hand contains primitives)
                    try:
                        self.card_index = coordinator.last_game_state.hand.index(
                            self.card
                        )
                    except (ValueError, AttributeError):
                        # hand may contain primitive types instead of Card objects
                        # Fall back to using card_index if available
                        if self.card_index < 0:
                            raise Exception(
                                "Specified card for CardAction is not in hand (and no valid card_index provided)"
                            )
        if self.card_index == -1:
            raise Exception("Specified card for CardAction is not in hand")
        hand_card_index = self.card_index + 1
        if self.target_monster is not None:
            self.target_index = self.target_monster.monster_index
        if self.target_index is None:
            coordinator.send_message("{} {}".format(self.command, hand_card_index))
        else:
            coordinator.send_message(
                "{} {} {}".format(self.command, hand_card_index, self.target_index)
            )


class PotionAction(Action):
    """An action to use or discard a selected potion"""

    def __init__(
        self, use, potion=None, potion_index=-1, target_monster=None, target_index=None
    ):
        super().__init__("potion")
        self.use = use
        self.potion = potion
        self.potion_index = potion_index
        self.target_monster = target_monster
        self.target_index = target_index

    def execute(self, coordinator):
        if self.potion is not None:
            raw_potions = getattr(coordinator.last_game_state, "potions", None)
            if raw_potions is not None:
                potions = raw_potions
            else:
                get_real_potions = getattr(
                    coordinator.last_game_state,
                    "get_real_potions",
                    None,
                )
                potions = get_real_potions() if callable(get_real_potions) else []
            self.potion_index = potions.index(self.potion)
        if self.potion_index == -1:
            raise Exception("Specified potion for PotionAction is not available")
        arguments = [self.command]
        if self.use:
            arguments.append("use")
        else:
            arguments.append("discard")
        arguments.append(str(self.potion_index))
        if self.target_monster is not None:
            self.target_index = self.target_monster.monster_index
        if self.target_index is not None:
            arguments.append(str(self.target_index))
        coordinator.send_message(" ".join(arguments))


class EndTurnAction(Action):
    """An action to end your turn"""

    def __init__(self):
        super().__init__("end")

    def execute(self, coordinator):
        import logging

        game = getattr(coordinator, "last_game_state", None)
        player = getattr(game, "player", None) if game else None
        energy = getattr(player, "energy", None)
        turn = getattr(game, "turn", None) if game else None
        floor = getattr(game, "floor", None) if game else None
        hand_size = len(getattr(game, "hand", []) or [])
        logging.info(
            "[TURN_END] floor=%s turn=%s energy_remaining=%s hand=%s",
            floor,
            turn,
            energy,
            hand_size,
        )
        super().execute(coordinator)


class ProceedAction(Action):
    """An action to use the CommunicationMod 'Proceed' command"""

    def __init__(self):
        super().__init__("proceed")


class LeaveAction(Action):
    """An action to use the CommunicationMod 'Leave' command (e.g., leave shop)"""

    def __init__(self):
        super().__init__("leave")


class ConfirmAction(Action):
    """An action to use the CommunicationMod 'Confirm' command (e.g., confirm card selection)"""

    def __init__(self):
        super().__init__("confirm", requires_game_ready=False)


class CancelAction(Action):
    """An action to use the CommunicationMod 'Cancel' command"""

    def __init__(self):
        super().__init__("cancel")


class WaitAction(Action):
    """An action to use the CommunicationMod 'Wait' command to trigger a state update"""

    def __init__(self, timeout=1):
        super().__init__("wait", requires_game_ready=False)
        self.timeout = timeout

    def execute(self, coordinator):
        coordinator.send_message(f"{self.command} {self.timeout}", wait_for_response=False)


class ClickAction(Action):
    """An action to use the CommunicationMod 'Click' command"""

    def __init__(self, target):
        super().__init__("click", requires_game_ready=False)
        self.target = target

    def execute(self, coordinator):
        payload = self._resolve_payload(coordinator)
        coordinator.send_message(f"{self.command} {payload}", wait_for_response=False)

    def _resolve_payload(self, coordinator):
        if isinstance(self.target, (list, tuple)):
            if len(self.target) >= 2 and self.target[0] == "card":
                card_index = self.target[1]
                screen = getattr(coordinator.last_game_state, "screen", None)
                positions = getattr(screen, "card_positions", []) if screen else []
                if 0 <= card_index < len(positions):
                    pos = positions[card_index]
                    if isinstance(pos, dict):
                        x = pos.get("x") or pos.get("center_x") or pos.get("cx")
                        y = pos.get("y") or pos.get("center_y") or pos.get("cy")
                        if x is not None and y is not None:
                            import logging

                            logging.debug(
                                f"GRID click resolved to coordinates: index={card_index}, x={x}, y={y}"
                            )
                            return f"{x} {y}"
                    elif isinstance(pos, (list, tuple)) and len(pos) >= 2:
                        import logging

                        logging.debug(
                            f"GRID click resolved to coordinates: index={card_index}, x={pos[0]}, y={pos[1]}"
                        )
                        return f"{pos[0]} {pos[1]}"
                import logging

                logging.debug(
                    "GRID click fallback (no positions): index=%s, target=%s",
                    card_index,
                    self.target,
                )
            return " ".join(str(part) for part in self.target)
        return str(self.target)


class KeyAction(Action):
    """An action to send a key command to CommunicationMod (e.g., confirm with enter)"""

    def __init__(self, key):
        super().__init__("key", requires_game_ready=False)
        self.key = key

    def execute(self, coordinator):
        import logging

        screen_type = getattr(coordinator.last_game_state, "screen_type", None)
        available = getattr(coordinator.last_game_state, "available_commands", None)
        logging.debug(
            "KEY action: key=%s, screen_type=%s, available=%s",
            self.key,
            screen_type,
            available,
        )
        coordinator.send_message(f"{self.command} {self.key}", wait_for_response=False)


class ChooseAction(Action):
    """An action to use the CommunicationMod 'Choose' command"""

    def __init__(self, choice_index=0, name=None):
        super().__init__("choose", requires_game_ready=True)
        self.choice_index = choice_index
        self.name = name

    def can_be_executed(self, coordinator):
        if super().can_be_executed(coordinator):
            return True

        game = getattr(coordinator, "last_game_state", None)
        if (
            getattr(game, "screen_type", None) == ScreenType.EVENT
            and "choose" in (getattr(game, "available_commands", None) or [])
        ):
            return True

        return False

    def execute(self, coordinator):
        if self.name is not None:
            coordinator.send_message(
                "{} {}".format(self.command, self.name), wait_for_response=False
            )
        else:
            coordinator.send_message(
                "{} {}".format(self.command, self.choice_index), wait_for_response=False
            )


class ChooseShopkeeperAction(ChooseAction):
    """An action to open the shop on a shop screen"""

    def __init__(self):
        super().__init__(name="shop")


class OpenChestAction(ChooseAction):
    """An action to open a chest on a chest screen"""

    def __init__(self):
        super().__init__(name="open")


class BuyCardAction(ChooseAction):
    """An action to buy a card in a shop"""

    def __init__(self, card):
        if not hasattr(card, "name"):
            raise ValueError(f"Card object missing 'name' attribute: {card}")
        super().__init__(name=card.name)

    def execute(self, coordinator):
        super().execute(coordinator)
        coordinator.add_action_to_queue(WaitAction(timeout=1))


class BuyPotionAction(ChooseAction):
    """An action to buy a potion in a shop. Currently, buys the first available potion of the same name."""

    def __init__(self, potion):
        super().__init__(name=potion.name)

    def execute(self, coordinator):
        if hasattr(coordinator.last_game_state, "has_potion_space"):
            has_space = coordinator.last_game_state.has_potion_space()
        else:
            has_space = not coordinator.last_game_state.are_potions_full()
        if not has_space:
            raise Exception("Cannot buy potion because potion slots are full.")
        super().execute(coordinator)
        coordinator.add_action_to_queue(WaitAction(timeout=1))


class BuyRelicAction(ChooseAction):
    """An action to buy a relic in a shop"""

    def __init__(self, relic):
        super().__init__(name=relic.name)

    def execute(self, coordinator):
        super().execute(coordinator)
        coordinator.add_action_to_queue(WaitAction(timeout=1))


class BuyPurgeAction(Action):
    """An action to buy a card removal at a shop"""

    def __init__(self, card_to_purge=None):
        super().__init__()
        self.card_to_purge = card_to_purge

    def execute(self, coordinator):
        if coordinator.last_game_state.screen_type != ScreenType.SHOP_SCREEN:
            raise Exception("BuyPurgeAction is only available on a Shop Screen")
        coordinator.add_action_to_queue(ChooseAction(name="purge"))
        if self.card_to_purge is not None:
            coordinator.add_action_to_queue(CardSelectAction([self.card_to_purge]))


class EventOptionAction(ChooseAction):
    """An action to choose an event option"""

    def __init__(self, option):
        super().__init__(choice_index=option.choice_index)


class RestAction(ChooseAction):
    """An action to choose a rest option at a rest site"""

    def __init__(self, rest_option):
        super().__init__(name=rest_option.name)


class CardRewardAction(ChooseAction):
    """An action to choose a card reward, or use Singing Bowl"""

    def __init__(self, card=None, bowl=False):
        if bowl:
            name = "bowl"
        elif card is not None:
            name = card.name
        else:
            raise Exception(
                "Must provide a card for CardRewardAction if not choosing the Singing Bowl"
            )
        super().__init__(name=name)


class CombatRewardAction(ChooseAction):
    """An action to choose a combat reward"""

    def __init__(self, combat_reward):
        self.combat_reward = combat_reward
        super().__init__()

    def execute(self, coordinator):
        if coordinator.last_game_state.screen_type != ScreenType.COMBAT_REWARD:
            raise Exception(
                "CombatRewardAction is only available on a Combat Reward Screen."
            )
        reward_list = coordinator.last_game_state.screen.rewards
        if self.combat_reward not in reward_list:
            raise Exception(
                "Reward is not available: {}".format(self.combat_reward.reward_type)
            )
        if (
            reward_type_name(self.combat_reward) == "POTION"
            and not _has_potion_space(coordinator.last_game_state)
        ):
            raise Exception("Cannot choose potion reward without potion space.")
        self.choice_index = reward_list.index(self.combat_reward)
        # Don't wait for response - combat reward selection often doesn't trigger state updates
        # Instead, rely on the next callback to continue
        super().execute(coordinator)


class BossRewardAction(ChooseAction):
    """An action to choose a boss relic"""

    def __init__(self, relic):
        super().__init__(name=relic.name)


class OptionalCardSelectConfirmAction(Action):
    """An action to click confirm on a hand or grid select screen, only if available"""

    def __init__(self, allow_stale_selection=False):
        super().__init__("confirm", requires_game_ready=False)
        self.allow_stale_selection = allow_stale_selection

    def execute(self, coordinator):
        import logging

        game_state = getattr(coordinator, "last_game_state", None)
        available = getattr(game_state, "available_commands", []) or []
        screen = getattr(game_state, "screen", None)
        screen_type = getattr(game_state, "screen_type", None)
        confirm_up = bool(getattr(screen, "confirm_up", False)) if screen else False
        stale_selection_screen = (
            self.allow_stale_selection
            and screen_type == ScreenType.GRID
            and any(command in available for command in ["choose", "key", "click"])
        )
        if ("confirm" in available and confirm_up) or stale_selection_screen:
            if stale_selection_screen and not ("confirm" in available and confirm_up):
                logging.warning(
                    "Sending card-select confirm with stale selection state: "
                    "screen=%s confirm_up=%s available=%s",
                    screen_type,
                    confirm_up,
                    available,
                )
            coordinator.send_message(self.command, wait_for_response=False)
            return
        logging.debug(
            "Skipping optional card-select confirm: screen=%s confirm_up=%s available=%s",
            screen_type,
            confirm_up,
            available,
        )



class CardSelectAction(Action):
    """An action to choose the selected cards on a hand or grid select screen"""

    def __init__(self, cards):
        self.cards = cards
        super().__init__()

    def execute(self, coordinator):
        screen_type = coordinator.last_game_state.screen_type
        screen = coordinator.last_game_state.screen
        if screen_type not in [ScreenType.HAND_SELECT, ScreenType.GRID]:
            raise Exception(
                "CardSelectAction is only available on a Hand Select or Grid Select Screen."
            )
        num_selected_cards = len(screen.selected_cards)
        num_remaining_cards = screen.num_cards - num_selected_cards
        available_cards = screen.cards
        if (
            screen_type == ScreenType.GRID
            and not screen.any_number
            and len(self.cards) != num_remaining_cards
        ):
            raise Exception(
                "Wrong number of cards selected (provided {}, need {})".format(
                    len(self.cards), num_remaining_cards
                )
            )
        elif len(self.cards) > num_remaining_cards:
            raise Exception(
                "Too many cards selected (provided {}, max {})".format(
                    len(self.cards), num_remaining_cards
                )
            )
        chosen_indices = []
        for card in self.cards:
            if card not in available_cards:
                raise Exception(
                    "Card {} is not available in the Hand Select Screen".format(
                        card.name
                    )
                )
            else:
                chosen_indices.append(available_cards.index(card))
        chosen_indices.sort(reverse=True)
        for index in chosen_indices:
            if screen_type == ScreenType.GRID:
                available = getattr(
                    coordinator.last_game_state, "available_commands", []
                )
                positions = getattr(screen, "card_positions", [])
                if "click" in available and positions:
                    coordinator.add_action_to_queue(ClickAction(("card", index, 0)))
                elif "choose" in available:
                    coordinator.add_action_to_queue(ChooseAction(choice_index=index))
                elif "key" in available:
                    coordinator.add_action_to_queue(KeyAction(f"CARD_{index + 1}"))
                else:
                    coordinator.add_action_to_queue(KeyAction(f"CARD_{index + 1}"))
            else:
                coordinator.add_action_to_queue(KeyAction(f"CARD_{index + 1}"))
        coordinator.add_action_to_queue(
            OptionalCardSelectConfirmAction(allow_stale_selection=True)
        )


class ChooseMapNodeAction(ChooseAction):
    """An action to choose a map node, other than the boss"""

    def __init__(self, node):
        self.node = node
        super().__init__()

    def execute(self, coordinator):
        if coordinator.last_game_state.screen_type != ScreenType.MAP:
            raise Exception("MapChoiceAction is only available on a Map Screen")
        next_nodes = coordinator.last_game_state.screen.next_nodes
        if self.node not in next_nodes:
            raise Exception("Node {} is not available to choose.".format(self.node))
        self.choice_index = next_nodes.index(self.node)
        super().execute(coordinator)


class ChooseMapBossAction(ChooseAction):
    """An action to choose the boss map node"""

    def __init__(self):
        super().__init__()

    def execute(self, coordinator):
        if coordinator.last_game_state.screen_type != ScreenType.MAP:
            raise Exception("ChooseMapBossAction is only available on a Map Screen")
        if not coordinator.last_game_state.screen.boss_available:
            raise Exception("The boss is not available to choose.")
        self.name = "boss"
        super().execute(coordinator)


class StartGameAction(Action):
    """An action to start a new game, if not already in a game"""

    def __init__(self, player_class, ascension_level=0, seed=None):
        super().__init__("start")
        self.player_class = player_class
        self.ascension_level = ascension_level
        self.seed = seed

    def execute(self, coordinator):
        arguments = [self.command, self.player_class.name, str(self.ascension_level)]
        if self.seed is not None:
            arguments.append(str(self.seed))
        coordinator.send_message(" ".join(arguments))


class StateAction(Action):
    """An action to use the CommunicationMod 'State' command"""

    def __init__(self, requires_game_ready=False):
        super().__init__(command="state", requires_game_ready=False)
