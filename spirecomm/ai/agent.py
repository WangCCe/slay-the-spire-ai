import time
import random
import logging
import sys
from datetime import datetime

from spirecomm.spire.game import Game
from spirecomm.spire.identifiers import potion_id
from spirecomm.spire.character import Intent, PlayerClass
from spirecomm.spire.numeric import coerce_int
from spirecomm.spire.screen import RestOption, reward_type_name
from spirecomm.communication.action import *
from spirecomm.ai.incoming_damage import (
    known_unknown_move_has_no_immediate_damage,
    known_unknown_move_immediate_damage,
)
from spirecomm.ai.intent_utils import intent_is_unknown, monster_intends_attack
from spirecomm.ai.priorities import *
from spirecomm.ai.heuristics.card_upgrades import (
    BLOCK_UPGRADE_BONUS,
    DAMAGE_UPGRADE_BONUS,
    card_upgrade_count,
    is_card_upgraded,
)
from spirecomm.ai.heuristics.card_names import canonical_card_name
from spirecomm.ai.heuristics.card_costs import effective_card_cost
from spirecomm.ai.heuristics.card_types import (
    card_is_playable,
    card_requires_target,
    card_type_name,
    is_attack_card,
)
from spirecomm.ai.heuristics.combat_state import power_signature
from spirecomm.ai.heuristics.potions import (
    game_real_potions,
    potion_can_use,
    potion_is_exhaust_hand_select,
)

# Note: Logging is configured in main.py to write to ai_debug.log
# No need to configure here

# Get logger for this module
logger = logging.getLogger(__name__)

# Import optimized AI components
try:
    from spirecomm.ai.decision.base import DecisionContext
    from spirecomm.ai.heuristics.card import SynergyCardEvaluator
    from spirecomm.ai.heuristics.simulation import HeuristicCombatPlanner
    from spirecomm.ai.heuristics.deck import DeckAnalyzer
    from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter

    OPTIMIZED_AI_AVAILABLE = True
except ImportError:
    OPTIMIZED_AI_AVAILABLE = False
    DecisionContext = None
    AdaptiveMapRouter = None

# Import tracker separately (always available, no dependencies)
try:
    from spirecomm.ai.tracker import GameTracker
except ImportError:
    GameTracker = None


class SimpleAgent:
    SHOP_PURGE_TARGET_KEYS = {
        "strike",
        "defend",
        "ascendersbane",
        "curseofthebell",
        "writhe",
        "injury",
        "clumsy",
        "doubt",
        "shame",
        "regret",
        "pain",
        "parasite",
        "normality",
        "decay",
        "necronomicurse",
        "pride",
    }

    def __init__(self, chosen_class=PlayerClass.THE_SILENT, elite_mode=None):
        self.game = Game()
        self.errors = 0
        self.choose_good_card = False
        self.skipped_cards = False
        self.visited_shop = False
        self.shop_purchase_made = False
        self._shop_purchase_signature = None
        self._leaving_shop_room = False
        self._shop_exit_waits = 0
        self.map_route = []
        self._last_route_hp_pct = None
        self._last_route_floor = None
        self._map_replan_hp_drop = 0.10
        self.chosen_class = chosen_class
        self.priorities = Priority()
        self.map_router = None
        self.elite_mode = elite_mode
        self.change_class(chosen_class)

    def change_class(self, new_class):
        self.chosen_class = new_class
        if self.chosen_class == PlayerClass.THE_SILENT:
            self.priorities = SilentPriority()
        elif self.chosen_class == PlayerClass.IRONCLAD:
            self.priorities = IroncladPriority()
        elif self.chosen_class == PlayerClass.DEFECT:
            self.priorities = DefectPowerPriority()
        else:
            self.priorities = random.choice(list(PlayerClass))
        if AdaptiveMapRouter is not None:
            player_class_str = str(self.chosen_class).replace("PlayerClass.", "")
            self.map_router = AdaptiveMapRouter(player_class=player_class_str, elite_mode=self.elite_mode)

    def handle_error(self, error):
        # Log the error and return a safe action instead of raising
        import logging

        logging.error(f"Game error: {error}")
        # Return StateAction to get current state instead of raising
        return StateAction()

    def _normalize_card_name(self, card):
        if card is None:
            return ""
        return canonical_card_name(card).replace("_", " ")

    @staticmethod
    def _compact_card_key(value):
        return "".join(ch for ch in str(value or "") if ch.isalnum()).lower()

    def _card_id_for_tracking(self, card):
        card_id = getattr(card, "card_id", None)
        if card_id:
            return str(card_id)
        return canonical_card_name(card)

    def _card_ids_for_tracking(self, cards):
        return [self._card_id_for_tracking(card) for card in cards]

    @staticmethod
    def _safe_float(value, default=0.0):
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _get_upgrade_bonus(self, card):
        if is_card_upgraded(card):
            return 0
        base_name = self._normalize_card_name(card)
        bonus = 0
        if base_name in DAMAGE_UPGRADE_BONUS:
            bonus += DAMAGE_UPGRADE_BONUS[base_name]
        if base_name in BLOCK_UPGRADE_BONUS:
            bonus += BLOCK_UPGRADE_BONUS[base_name]
        if bonus == 0:
            card_type = card_type_name(card)
            if card_type == "ATTACK":
                bonus = 2
            elif card_type == "SKILL":
                bonus = 2
            elif card_type == "POWER":
                bonus = 1
            else:
                bonus = 1
        return bonus

    def _score_upgrade_candidate(self, card, context=None):
        if is_card_upgraded(card):
            return -999.0
        bonus = self._get_upgrade_bonus(card)
        priority_rank = self.priorities.CARD_PRIORITIES_BY_NAME.get(
            self._normalize_card_name(card)
        )
        priority_boost = 0.0
        if priority_rank is not None:
            list_len = max(len(self.priorities.CARD_PRIORITY_LIST), 1)
            priority_boost = (list_len - priority_rank) * 0.5
        synergy_boost = 0.0
        if context is not None and hasattr(self, "card_evaluator") and self.card_evaluator:
            try:
                eval_score = self.card_evaluator.evaluate_card(card, context)
                synergy_boost = eval_score / 20.0
            except Exception:
                pass
        return priority_boost * 2.0 + bonus * 1.5 + synergy_boost

    def _best_upgrade_score(self, context=None):
        if not hasattr(self.game, "deck") or not self.game.deck:
            return 0.0
        best_score = 0.0
        for card in self.game.deck:
            score = self._score_upgrade_candidate(card, context)
            if score > best_score:
                best_score = score
        return best_score

    # === Shop Helper Methods ===

    def _exit_shop(self):
        """Return appropriate action to exit shop."""
        self._leaving_shop_room = True
        available = set(getattr(self.game, "available_commands", []) or [])
        screen_type = getattr(self.game, "screen_type", None)

        if (
            screen_type == ScreenType.SHOP_SCREEN
            and getattr(self, "shop_purchase_made", False)
            and "proceed" not in available
        ):
            can_cancel = (
                "cancel" in available
                or "return" in available
                or "leave" in available
                or "skip" in available
                or getattr(self.game, "cancel_available", False)
            )
            exit_waits = getattr(self, "_shop_exit_waits", 0)
            if not can_cancel or exit_waits < 2:
                self._shop_exit_waits = exit_waits + 1
                logging.info(
                    "[SHOP_SCREEN] Waiting for post-purchase exit state (%s/2), can_cancel=%s",
                    self._shop_exit_waits,
                    can_cancel,
                )
                return WaitAction(timeout=1)
            self._shop_exit_waits = 0
            logging.info("[SHOP_SCREEN] Post-purchase exit stable, sending cancel")
            return CancelAction()
        if "leave" in available:
            self._shop_exit_waits = 0
            return LeaveAction()
        if "proceed" in available or getattr(self.game, "proceed_available", False):
            self._shop_exit_waits = 0
            return ProceedAction()
        if (
            "cancel" in available
            or "return" in available
            or "skip" in available
            or getattr(self.game, "cancel_available", False)
        ):
            self._shop_exit_waits = 0
            return CancelAction()
        if screen_type == ScreenType.SHOP_SCREEN:
            self._shop_exit_waits = 0
            return LeaveAction()
        self._shop_exit_waits = 0
        return ProceedAction()

    def _shop_state_signature(self, gold, screen):
        return (
            self._safe_int(gold, 0),
            bool(getattr(screen, "purge_available", False)),
            len(getattr(screen, "cards", []) or []),
            len(getattr(screen, "relics", []) or []),
            len(getattr(screen, "potions", []) or []),
        )

    def _mark_shop_purchase(self, gold, screen):
        self.shop_purchase_made = True
        self._shop_purchase_signature = self._shop_state_signature(gold, screen)
        self._shop_exit_waits = 0

    def _has_paid_shop_purge_target(self):
        for card in getattr(self.game, "deck", []) or []:
            keys = {
                self._compact_card_key(self._normalize_card_name(card)),
                self._compact_card_key(getattr(card, "card_id", "")),
                self._compact_card_key(getattr(card, "name", "")),
            }
            if keys & self.SHOP_PURGE_TARGET_KEYS:
                return True
        return False

    def _validate_shop_cards(self, screen):
        """Validate that shop cards have required attributes."""
        if not hasattr(screen, "cards") or not screen.cards:
            logging.warning("[SHOP_SCREEN] No cards listed, exiting shop")
            return []

        valid_cards = []
        for card in screen.cards:
            if (
                hasattr(card, "card_id")
                and hasattr(card, "name")
                and hasattr(card, "price")
            ):
                valid_cards.append(card)
            else:
                card_info = f"card_id={getattr(card, 'card_id', 'MISSING')}, name={getattr(card, 'name', 'MISSING')}, price={getattr(card, 'price', 'MISSING')}"
                logging.warning(f"[SHOP_SCREEN] Skipping invalid card: {card_info}")
                print(
                    f"[SHOP_SCREEN WARNING] Skipping invalid card: {card_info}",
                    file=sys.stderr,
                )

        if not valid_cards:
            logging.warning("[SHOP_SCREEN] No valid cards found")
        return valid_cards

    def _has_potion_space(self):
        """Check if there is room for another potion."""
        if hasattr(self.game, "has_potion_space"):
            return self.game.has_potion_space()
        return not self.game.are_potions_full()

    def _should_buy_card(self, card, gold, purge_cost, screen):
        """Determine if a card should be purchased."""
        try:
            if not hasattr(card, "price") or not hasattr(card, "card_id"):
                return False

            gold = self._safe_int(gold, 0)
            price = self._safe_int(card.price, None)
            if price is None:
                return False

            if gold >= price and not self.priorities.should_skip(card):
                if not self._shop_card_is_cash_worthy(card):
                    return False
                if not screen.purge_available or gold - price >= purge_cost:
                    return True
        except Exception as e:
            card_id = getattr(card, "card_id", "UNKNOWN")
            logging.error(f"[SHOP_SCREEN] Error evaluating card {card_id}: {e}")
            print(
                f"[SHOP_SCREEN] Error evaluating card {card_id}: {e}", file=sys.stderr
            )
        return False

    def _shop_card_is_cash_worthy(self, card):
        """Shop buys need a higher bar than free reward picks."""
        card_name = self._normalize_card_name(card)
        low_reliability_cards = {
            "Havoc",
            "Deep Breath",
            "Impatience",
            "Forethought",
            "Rage",
        }
        if card_name in low_reliability_cards:
            logging.info(
                "[SHOP_SCREEN] Skipping low-reliability shop card: %s",
                card_name,
            )
            return False

        deck_strategy = getattr(self, "deck_strategy", None)
        if deck_strategy is not None and DecisionContext is not None:
            try:
                context = DecisionContext(self.game)
                should_pick, reason = deck_strategy.should_pick_card(card, context)
            except Exception as exc:
                logging.info(
                    "[SHOP_SCREEN] Deck strategy unavailable for %s: %s",
                    card_name,
                    exc,
                )
            else:
                if not should_pick:
                    logging.info(
                        "[SHOP_SCREEN] Skipping shop card %s: %s",
                        card_name,
                        reason,
                    )
                    return False

        return True

    def _should_buy_relic(self, relic, gold):
        """Determine if a relic should be purchased."""
        try:
            gold = self._safe_int(gold, 0)
            price = self._safe_int(getattr(relic, "price", None), None)
            if price is None:
                return False

            if gold >= price and price <= gold * 0.7:
                useful_relics = [
                    "Burning Blood",
                    "Barricade",
                    "Demon Form",
                    "Limit Break",
                    "Juggernaut",
                    "Runic Pyramid",
                    "Sundial",
                    "Twin Daggers",
                    "Cloak Clasp",
                    "Gremlin Horn",
                ]
                if relic.name in useful_relics or gold >= price + 50:
                    return True
        except Exception as e:
            relic_name = getattr(relic, "name", "UNKNOWN")
            logging.error(f"[SHOP_SCREEN] Error evaluating relic {relic_name}: {e}")
            print(
                f"[SHOP_SCREEN] Error evaluating relic {relic_name}: {e}",
                file=sys.stderr,
            )
        return False

    def _log_shop_error(self, e, context=""):
        """Log shop error with traceback."""
        import traceback

        error_msg = f"[SHOP_SCREEN ERROR{context}] {type(e).__name__}: {e}"
        card_list = (
            [
                getattr(c, "card_id", "INVALID")
                for c in getattr(self.game.screen, "cards", [])
            ]
            if hasattr(self.game, "screen")
            else "NO_CARDS"
        )

        logging.error(error_msg)
        logging.error(f"[SHOP_SCREEN ERROR] Cards: {card_list}")
        logging.error(f"[SHOP_SCREEN ERROR] Traceback:\n{traceback.format_exc()}")

        print(error_msg, file=sys.stderr)
        print(f"[SHOP_SCREEN ERROR] Cards: {card_list}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    def _available_event_choice_count(self):
        choices = getattr(self.game, "choice_list", None)
        if choices is not None:
            return len(choices)

        screen = getattr(self.game, "screen", None)
        options = getattr(screen, "options", None) or []
        enabled_options = [
            option for option in options if not getattr(option, "disabled", False)
        ]
        return len(enabled_options) if enabled_options else len(options)

    def _choose_event_option(self):
        screen = getattr(self.game, "screen", None)
        event_id = getattr(screen, "event_id", None)
        option_count = self._available_event_choice_count()
        risky_event_ids = {
            "Vampires",
            "Masked Bandits",
            "Knowing Skull",
            "Ghosts",
            "Liars Game",
            "Golden Idol",
            "Golden Shrine",
            "GoldenShrine",
            "Drug Dealer",
            "The Library",
            "NoteForYourself",
            "Note For Yourself",
            "Dead Adventurer",
            "DeadAdventurer",
            "The Mausoleum",
            "Mausoleum",
            "Mushrooms",
            "The Mushroom Lair",
        }
        legacy_last_safe_events = risky_event_ids - {"Masked Bandits"}

        if option_count <= 0:
            logger.warning(
                "[EVENT_GUARD] No available choices for event=%s; defaulting to choose 0",
                event_id,
            )
            return ChooseAction(0)

        def _choice_label(option):
            return str(
                getattr(option, "label", None)
                or getattr(option, "text", None)
                or option
                or ""
            )

        choice_labels = [_choice_label(option) for option in (getattr(self.game, "choice_list", None) or [])]
        screen_labels = [_choice_label(option) for option in (getattr(screen, "options", None) or [])]
        labels_for_selection = choice_labels[:option_count] or screen_labels[:option_count]

        choice_index = 0
        if event_id in {"Mushrooms", "The Mushroom Lair"}:
            safe_keywords = ("leave", "ignore", "refuse", "decline", "move on", "skip")
            for idx, label in enumerate(labels_for_selection):
                normalized_label = label.lower()
                if any(keyword in normalized_label for keyword in safe_keywords):
                    choice_index = idx
                    break
            else:
                raw_current_hp = getattr(self.game, "current_hp", None)
                raw_max_hp = getattr(self.game, "max_hp", None)
                current_hp = self._safe_float(raw_current_hp, 0.0)
                max_hp = max(self._safe_float(raw_max_hp, 0.0), 1.0)
                hp_known = raw_current_hp is not None and raw_max_hp is not None
                hp_pct = current_hp / max_hp if hp_known else 1.0
                weak_hp_margin_before_act1_boss = (
                    hp_known
                    and self._safe_int(getattr(self.game, "act", 0), 0) == 1
                    and self._safe_int(getattr(self.game, "floor", 0), 0) >= 7
                    and hp_pct <= 0.8
                )
                preferred_keywords = (
                    ("eat", "heal")
                    if weak_hp_margin_before_act1_boss
                    else ("fight", "stomp")
                )
                fallback_keywords = (
                    ("fight", "stomp")
                    if weak_hp_margin_before_act1_boss
                    else ("eat", "heal")
                )
                for idx, label in enumerate(labels_for_selection):
                    normalized_label = label.lower()
                    if any(keyword in normalized_label for keyword in preferred_keywords):
                        choice_index = idx
                        break
                else:
                    for idx, label in enumerate(labels_for_selection):
                        normalized_label = label.lower()
                        if any(keyword in normalized_label for keyword in fallback_keywords):
                            choice_index = idx
                            break
        elif event_id in {"Forgotten Altar", "ForgottenAltar"}:
            safe_keywords = (
                "leave",
                "ignore",
                "refuse",
                "decline",
                "move on",
                "skip",
                "offer",
            )
            for idx, label in enumerate(labels_for_selection):
                normalized_label = label.lower()
                if any(keyword in normalized_label for keyword in safe_keywords):
                    choice_index = idx
                    break
            else:
                raw_current_hp = getattr(self.game, "current_hp", None)
                raw_max_hp = getattr(self.game, "max_hp", None)
                current_hp = self._safe_float(raw_current_hp, 0.0)
                max_hp = max(self._safe_float(raw_max_hp, 0.0), 1.0)
                hp_known = raw_current_hp is not None and raw_max_hp is not None
                critical_hp = hp_known and (
                    current_hp <= 20 or current_hp / max_hp <= 0.35
                )
                preferred_keywords = ("desecrate",) if critical_hp else ("sacrifice",)
                fallback_keywords = (
                    ("sacrifice", "desecrate") if critical_hp else ("desecrate",)
                )
                for idx, label in enumerate(labels_for_selection):
                    normalized_label = label.lower()
                    if any(keyword in normalized_label for keyword in preferred_keywords):
                        choice_index = idx
                        break
                else:
                    for idx, label in enumerate(labels_for_selection):
                        normalized_label = label.lower()
                        if any(keyword in normalized_label for keyword in fallback_keywords):
                            choice_index = idx
                            break
        elif event_id in {"Shining Light", "ShiningLight"}:
            raw_current_hp = getattr(self.game, "current_hp", None)
            raw_max_hp = getattr(self.game, "max_hp", None)
            current_hp = self._safe_float(raw_current_hp, 0.0)
            max_hp = max(self._safe_float(raw_max_hp, 0.0), 1.0)
            hp_known = raw_current_hp is not None and raw_max_hp is not None
            post_event_hp_pct = (current_hp - max_hp * 0.30) / max_hp
            should_leave = hp_known and post_event_hp_pct < 0.60
            preferred_keywords = (
                ("leave", "ignore", "decline", "skip")
                if should_leave
                else ("enter", "upgrade", "light")
            )
            fallback_keywords = (
                ("enter", "upgrade", "light")
                if should_leave
                else ("leave", "ignore", "decline", "skip")
            )
            for idx, label in enumerate(labels_for_selection):
                normalized_label = label.lower()
                if any(keyword in normalized_label for keyword in preferred_keywords):
                    choice_index = idx
                    break
            else:
                for idx, label in enumerate(labels_for_selection):
                    normalized_label = label.lower()
                    if any(keyword in normalized_label for keyword in fallback_keywords):
                        choice_index = idx
                        break
        elif event_id in {"Cursed Tome", "CursedTome"}:
            raw_current_hp = getattr(self.game, "current_hp", None)
            raw_max_hp = getattr(self.game, "max_hp", None)
            current_hp = self._safe_float(raw_current_hp, 0.0)
            max_hp = max(self._safe_float(raw_max_hp, 0.0), 1.0)
            hp_known = raw_current_hp is not None and raw_max_hp is not None
            estimated_read_damage = max_hp * 0.20
            should_leave_before_reading = (
                hp_known
                and (current_hp - estimated_read_damage) / max_hp < 0.60
                and any("read" in label.lower() for label in labels_for_selection)
            )
            if should_leave_before_reading:
                preferred_keywords = ("leave", "stop")
            elif any("take" in label.lower() for label in labels_for_selection):
                preferred_keywords = ("take", "book")
            else:
                preferred_keywords = ("read", "continue")
            fallback_keywords = (
                ("read", "continue", "take", "book")
                if should_leave_before_reading
                else ("leave", "stop")
            )
            for idx, label in enumerate(labels_for_selection):
                normalized_label = label.lower()
                if any(keyword in normalized_label for keyword in preferred_keywords):
                    choice_index = idx
                    break
            else:
                for idx, label in enumerate(labels_for_selection):
                    normalized_label = label.lower()
                    if any(keyword in normalized_label for keyword in fallback_keywords):
                        choice_index = idx
                        break
        elif event_id in risky_event_ids:
            safe_keywords = ("leave", "ignore", "refuse", "decline", "move on", "skip")
            if event_id == "Masked Bandits":
                safe_keywords = ("pay", "give gold", "leave")

            for idx, label in enumerate(labels_for_selection):
                normalized_label = label.lower()
                if any(keyword in normalized_label for keyword in safe_keywords):
                    choice_index = idx
                    break
            else:
                choice_index = option_count - 1 if event_id in legacy_last_safe_events else 0

        logger.info(
            "[EVENT_GUARD] event=%s choices=%s screen_options=%s selected=%s choice_labels=%s screen_labels=%s",
            event_id,
            len(getattr(self.game, "choice_list", []) or []),
            len(getattr(screen, "options", []) or []),
            choice_index,
            choice_labels,
            screen_labels,
        )
        return ChooseAction(choice_index)

    def get_next_action_in_game(self, game_state):
        self.game = game_state
        # time.sleep(0.07)
        try:
            if self.game.choice_available:
                return self.handle_screen()
            if self.game.proceed_available:
                return ProceedAction()
            if self.game.play_available:
                # Potions are now integrated into beam search for OptimizedAgent
                # Fallback: use potions in dangerous situations outside of beam search
                if len(self.game.get_real_potions()) > 0:
                    danger_level = self._evaluate_combat_danger(None)
                    # Use potions in high-danger situations (>0.6) or in elite/boss fights
                    if (
                        danger_level > 0.6
                        or "Elite" in self.game.room_type
                        or "Boss" in self.game.room_type
                    ):
                        potion_action = self.use_next_potion()
                        if potion_action is not None:
                            return potion_action
                return self.get_play_card_action()
            if self.game.end_available:
                return EndTurnAction()
            if self.game.cancel_available:
                return CancelAction()
        except Exception as e:
            # Fallback to safe action on error
            # Use stderr for error output to avoid interfering with Communication Mod
            import sys

            print(f"Error in get_next_action_in_game: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            if self.game.end_available:
                return EndTurnAction()
            return ProceedAction()

    def get_next_action_out_of_game(self):
        # ScreenType.NONE typically indicates main menu/attract mode
        # Always return StartGameAction for out-of-game states
        return StartGameAction(self.chosen_class)

    def is_monster_attacking(self):
        for monster in self.game.monsters:
            intent = getattr(monster, "intent", None)
            if monster_intends_attack(monster, missing_intent_counts=False) or intent_is_unknown(intent):
                return True
        return False

    @staticmethod
    def _safe_int(value, default=0):
        return coerce_int(value, default)

    @classmethod
    def _monster_current_hp(cls, monster, default=0):
        value = getattr(monster, "current_hp", None)
        if value is None:
            return default
        return cls._safe_int(value, default=default)

    @classmethod
    def _is_live_monster(cls, monster):
        return (
            cls._monster_current_hp(monster, default=1) > 0
            and not getattr(monster, "is_gone", False)
            and not getattr(monster, "half_dead", False)
        )

    @staticmethod
    def _positive_move_hits(monster):
        return max(1, SimpleAgent._safe_int(getattr(monster, "move_hits", 1), 1))

    @classmethod
    def _move_damage_contribution(cls, monster):
        damage = getattr(monster, "move_adjusted_damage", None)
        if damage is None:
            return 0
        return max(0, cls._safe_int(damage, 0)) * cls._positive_move_hits(monster)

    def get_incoming_damage(self):
        incoming_damage = 0
        for monster in self.game.monsters:
            if self._is_live_monster(monster):
                if (
                    getattr(monster, "move_adjusted_damage", None) is not None
                    and monster_intends_attack(monster)
                ):
                    incoming_damage += self._move_damage_contribution(monster)
                elif intent_is_unknown(getattr(monster, "intent", None)):
                    known_damage = known_unknown_move_immediate_damage(monster)
                    if known_damage > 0:
                        incoming_damage += known_damage
                        continue
                    if known_unknown_move_has_no_immediate_damage(monster):
                        continue
                    incoming_damage += 5 * self._safe_int(getattr(self.game, "act", 1), default=1)
        return incoming_damage

    def get_low_hp_target(self):
        available_monsters = [
            monster
            for monster in self.game.monsters
            if self._is_live_monster(monster)
        ]
        best_monster = min(available_monsters, key=lambda x: self._monster_current_hp(x))
        return best_monster

    def get_high_hp_target(self):
        available_monsters = [
            monster
            for monster in self.game.monsters
            if self._is_live_monster(monster)
        ]
        best_monster = max(available_monsters, key=lambda x: self._monster_current_hp(x))
        return best_monster

    def many_monsters_alive(self):
        available_monsters = [
            monster
            for monster in self.game.monsters
            if self._is_live_monster(monster)
        ]
        return len(available_monsters) > 1

    def _card_requires_target(self, card):
        aoe_names = getattr(self.priorities, "AOE_CARD_NAMES", ())
        return card_requires_target(card, aoe_names)

    def get_play_card_action(self):
        playable_cards = [card for card in self.game.hand if card_is_playable(card)]
        available_energy = getattr(getattr(self.game, "player", None), "energy", None)
        zero_cost_cards = [
            card
            for card in playable_cards
            if effective_card_cost(card, available_energy) == 0
        ]
        zero_cost_attacks = [
            card
            for card in zero_cost_cards
            if is_attack_card(card)
        ]
        zero_cost_non_attacks = [
            card
            for card in zero_cost_cards
            if not is_attack_card(card)
        ]
        nonzero_cost_cards = [
            card
            for card in playable_cards
            if effective_card_cost(card, available_energy) != 0
        ]
        aoe_cards = [
            card for card in playable_cards if self.priorities.is_card_aoe(card)
        ]
        # If any monsters are at 1 HP (Neow's Blessing, etc.), prioritize cleanup attacks.
        low_hp_monsters = [
            monster
            for monster in self.game.monsters
            if self._is_live_monster(monster)
            and self._monster_current_hp(monster) <= 1
        ]
        if low_hp_monsters:
            attack_cards = [
                card
                for card in playable_cards
                if is_attack_card(card)
            ]
            if attack_cards:
                import logging

                if self.many_monsters_alive() and aoe_cards:
                    card_to_play = self.priorities.get_best_card_to_play(aoe_cards)
                else:
                    card_to_play = self.priorities.get_best_card_to_play(attack_cards)
                logging.info(
                    f"[SIMPLE_AGENT_LETHAL] Cleanup attack selected: {self._card_id_for_tracking(card_to_play)}"
                )
                if self._card_requires_target(card_to_play):
                    target = self.get_low_hp_target()
                    return PlayCardAction(card=card_to_play, target_monster=target)
                return PlayCardAction(card=card_to_play)
        incoming_damage = self.get_incoming_damage()
        player_block = self._safe_int(getattr(self.game.player, "block", 0))
        act = self._safe_int(getattr(self.game, "act", 1), default=1)
        defense_threshold = incoming_damage - (act + 4)
        if player_block > defense_threshold:
            import logging

            logging.info(
                f"[SIMPLE_AGENT_DEFENSE] Skipping defensive cards - block={player_block}, "
                f"incoming={incoming_damage}, threshold={defense_threshold}, "
                f"act={act}"
            )
            offensive_cards = [
                card
                for card in nonzero_cost_cards
                if not self.priorities.is_card_defensive(card)
            ]
            if len(offensive_cards) > 0:
                nonzero_cost_cards = offensive_cards
            else:
                nonzero_cost_cards = [
                    card for card in nonzero_cost_cards if not card.exhausts
                ]
        if len(playable_cards) == 0:
            return EndTurnAction()
        if len(zero_cost_non_attacks) > 0:
            card_to_play = self.priorities.get_best_card_to_play(zero_cost_non_attacks)
        elif len(nonzero_cost_cards) > 0:
            card_to_play = self.priorities.get_best_card_to_play(nonzero_cost_cards)
            if (
                len(aoe_cards) > 0
                and self.many_monsters_alive()
                and is_attack_card(card_to_play)
            ):
                card_to_play = self.priorities.get_best_card_to_play(aoe_cards)
        elif len(zero_cost_attacks) > 0:
            card_to_play = self.priorities.get_best_card_to_play(zero_cost_attacks)
        else:
            # This shouldn't happen!
            return EndTurnAction()
        if self._card_requires_target(card_to_play):
            available_monsters = [
                monster
                for monster in self.game.monsters
                if self._is_live_monster(monster)
            ]
            if len(available_monsters) == 0:
                return EndTurnAction()
            if is_attack_card(card_to_play):
                target = self.get_low_hp_target()
            else:
                target = self.get_high_hp_target()
            return PlayCardAction(card=card_to_play, target_monster=target)
        else:
            return PlayCardAction(card=card_to_play)

    def use_next_potion(self):
        for potion in self.game.get_real_potions():
            if potion_can_use(potion) and not potion_is_exhaust_hand_select(potion):
                if getattr(potion, "requires_target", False):
                    return PotionAction(
                        True, potion=potion, target_monster=self.get_low_hp_target()
                    )
                else:
                    return PotionAction(True, potion=potion)

    def handle_screen(self):
        if self.game.screen_type == ScreenType.EVENT:
            return self._choose_event_option()
        elif self.game.screen_type == ScreenType.CHEST:
            return OpenChestAction()
        elif self.game.screen_type == ScreenType.SHOP_ROOM:
            if getattr(self, "_leaving_shop_room", False):
                self.visited_shop = False
                self.shop_purchase_made = False
                self._shop_purchase_signature = None
                return self._exit_shop()
            if not self.visited_shop:
                self.visited_shop = True
                self.shop_purchase_made = False
                self._shop_purchase_signature = None
                return ChooseShopkeeperAction()
            else:
                self.visited_shop = False
                self.shop_purchase_made = False
                self._shop_purchase_signature = None
                return self._exit_shop()
        elif self.game.screen_type == ScreenType.REST:
            return self.choose_rest_option()
        elif self.game.screen_type == ScreenType.CARD_REWARD:
            return self.choose_card_reward()
        elif self.game.screen_type == ScreenType.COMBAT_REWARD:
            import sys

            rewards = (
                self.game.screen.rewards if hasattr(self.game.screen, "rewards") else []
            )
            logging.info(
                f"[COMBAT_REWARD] Floor {self.game.floor if hasattr(self.game, 'floor') else '?'}: {len(rewards)} rewards, skipped_cards={self.skipped_cards}\n"
            )

            for i, reward_item in enumerate(rewards):
                reward_type = reward_type_name(reward_item)
                skip_potion = reward_type == "POTION" and not self._has_potion_space()
                skip_card = reward_type == "CARD" and self.skipped_cards
                logging.info(
                    f"  [{i}] type={reward_item.reward_type}, skip_potion={skip_potion}, skip_card={skip_card}\n"
                )

            for reward_item in rewards:
                reward_type = reward_type_name(reward_item)
                if reward_type == "POTION" and not self._has_potion_space():
                    continue
                elif reward_type == "CARD" and self.skipped_cards:
                    continue
                else:
                    logging.info(
                        f"[COMBAT_REWARD] Taking reward: {reward_item.reward_type}\n"
                    )
                    return CombatRewardAction(reward_item)
            logging.info(f"[COMBAT_REWARD] Proceeding (all rewards skipped)\n")
            return ProceedAction()
        elif self.game.screen_type == ScreenType.MAP:
            # Reset skipped_cards flag when we reach the map (combat rewards fully processed)
            self.skipped_cards = False
            self._leaving_shop_room = False
            return self.make_map_choice()
        elif self.game.screen_type == ScreenType.BOSS_REWARD:
            relics = self.game.screen.relics
            best_boss_relic = self.priorities.get_best_boss_relic(relics)
            return BossRewardAction(best_boss_relic)
        elif self.game.screen_type == ScreenType.SHOP_SCREEN:
            try:
                gold = self._safe_int(getattr(self.game, "gold", 0), 0)
                screen = self.game.screen

                cancel_available = getattr(self.game, "cancel_available", False)
                proceed_available = getattr(self.game, "proceed_available", False)
                logging.info(
                    "[SHOP_SCREEN] gold=%s cards=%s relics=%s potions=%s purge_available=%s cancel_available=%s proceed_available=%s",
                    gold,
                    len(getattr(screen, "cards", []) or []),
                    len(getattr(screen, "relics", []) or []),
                    len(getattr(screen, "potions", []) or []),
                    getattr(screen, "purge_available", False),
                    cancel_available,
                    proceed_available,
                )

                if self.shop_purchase_made:
                    purchase_signature = getattr(self, "_shop_purchase_signature", None)
                    current_signature = self._shop_state_signature(gold, screen)
                    if (
                        purchase_signature is not None
                        and current_signature != purchase_signature
                    ):
                        logging.info(
                            "[SHOP_SCREEN] Purchase state changed; continuing shop evaluation"
                        )
                        self.shop_purchase_made = False
                        self._shop_purchase_signature = None
                        self._shop_exit_waits = 0
                    else:
                        logging.info("[SHOP_SCREEN] Purchase already made in this shop, exiting")
                        return self._exit_shop()

                # Validate screen.cards exists
                valid_cards = self._validate_shop_cards(screen)
                if not valid_cards:
                    return self._exit_shop()

                # Priority 1: Purge (card removal) if needed and affordable
                purge_cost = (
                    self._safe_int(screen.purge_cost, float("inf"))
                    if screen.purge_available
                    else float("inf")
                )
                has_paid_purge_target = self._has_paid_shop_purge_target()
                if (
                    screen.purge_available
                    and gold >= purge_cost
                    and has_paid_purge_target
                ):
                    self._mark_shop_purchase(gold, screen)
                    return ChooseAction(name="purge")

                # Priority 2: Buy cards that are good for the deck
                if hasattr(self.priorities, "get_sorted_cards"):
                    sorted_cards = self.priorities.get_sorted_cards(valid_cards)
                    for card in sorted_cards:
                        if self._should_buy_card(card, gold, purge_cost, screen):
                            self._mark_shop_purchase(gold, screen)
                            return BuyCardAction(card)
                else:
                    for card in valid_cards:
                        price = self._safe_int(getattr(card, "price", None), None)
                        if (
                            price is not None
                            and gold >= price
                            and not self.priorities.should_skip(card)
                        ):
                            self._mark_shop_purchase(gold, screen)
                            return BuyCardAction(card)

                # Priority 3: Buy useful relics (consider price and value)
                if hasattr(screen, "relics") and screen.relics:
                    for relic in screen.relics:
                        if self._should_buy_relic(relic, gold):
                            self._mark_shop_purchase(gold, screen)
                            return BuyRelicAction(relic)

                # Priority 4: Buy potions if needed and affordable
                if (
                    hasattr(screen, "potions")
                    and screen.potions
                    and self._has_potion_space()
                ):
                    for potion in screen.potions:
                        try:
                            price = self._safe_int(getattr(potion, "price", None), None)
                            if price is not None and gold >= price:
                                useful_potions = [
                                    "Healing Potion",
                                    "Strength Potion",
                                    "Fire Potion",
                                    "Ice Potion",
                                    "Block Potion",
                                    "Strawberry",
                                ]
                                if potion.name in useful_potions:
                                    self._mark_shop_purchase(gold, screen)
                                    return BuyPotionAction(potion)
                        except Exception as e:
                            potion_name = getattr(potion, "name", "UNKNOWN")
                            logging.error(
                                f"[SHOP_SCREEN] Error evaluating potion {potion_name}: {e}"
                            )
                            print(
                                f"[SHOP_SCREEN] Error evaluating potion {potion_name}: {e}",
                                file=sys.stderr,
                            )
                            continue

                # Priority 5: Purge as last resort if we have extra gold
                if (
                    screen.purge_available
                    and gold >= purge_cost
                    and has_paid_purge_target
                ):
                    self._mark_shop_purchase(gold, screen)
                    return ChooseAction(name="purge")
                if screen.purge_available and gold >= purge_cost:
                    logging.info(
                        "[SHOP_SCREEN] Skipping paid purge: no starter or curse removal target"
                    )

                # No good purchases available
                return self._exit_shop()
            except Exception as e:
                self._log_shop_error(e)
                return self._exit_shop()
        elif self.game.screen_type == ScreenType.GRID:
            # Check if we've already selected enough cards and should confirm
            screen = self.game.screen
            if hasattr(screen, 'selected_cards') and hasattr(screen, 'num_cards'):
                num_selected = len(screen.selected_cards)
                num_required = screen.num_cards
                confirm_up = screen.confirm_up if hasattr(screen, 'confirm_up') else False
                available = getattr(self.game, 'available_commands', [])

                # If we've selected enough cards and confirm is available, confirm immediately
                if num_selected >= num_required and confirm_up and "confirm" in available:
                    logging.info(
                        f"[GRID_SCREEN] Already selected {num_selected}/{num_required} cards, confirming"
                    )
                    return ConfirmAction()

            # For GRID screen, check if we can select cards based on screen state
            can_select = self.game.choice_available or (
                hasattr(self.game, "screen")
                and self.game.screen is not None
                and hasattr(self.game.screen, "num_cards")
                and self.game.screen.num_cards > 0
                and len(self.game.screen.cards) > 0
            )
            logging.debug(
                f"[GRID_SCREEN] screen_type=GRID, choice_available={self.game.choice_available}, can_select={can_select}, for_upgrade={self.game.screen.for_upgrade if hasattr(self.game.screen, 'for_upgrade') else 'N/A'}"
            )
            if not can_select:
                logging.debug(
                    "[GRID_SCREEN] cannot select cards, returning ProceedAction()"
                )
                return ProceedAction()
            logging.debug(
                f"[GRID_SCREEN] Checking for_upgrade={self.game.screen.for_upgrade if hasattr(self.game.screen, 'for_upgrade') else 'N/A'}, choose_good_card={self.choose_good_card}"
            )
            screen = self.game.screen
            for_upgrade = bool(getattr(screen, "for_upgrade", False))
            for_purge = bool(getattr(screen, "for_purge", False))
            for_transform = bool(getattr(screen, "for_transform", False))
            if for_upgrade:
                # For upgrade: pick best cards
                logging.debug(
                    f"[GRID_SCREEN] Calling get_sorted_cards for {len(self.game.screen.cards)} cards"
                )
                context = None
                if DecisionContext is not None:
                    try:
                        context = DecisionContext(self.game)
                    except Exception:
                        context = None
                available_cards = sorted(
                    self.game.screen.cards,
                    key=lambda c: self._score_upgrade_candidate(c, context),
                    reverse=True,
                )
                logging.debug(
                    f"[GRID_SCREEN] Got {len(available_cards)} sorted cards: {self._card_ids_for_tracking(available_cards)}"
                )
            elif for_purge or for_transform:
                # For purge/remove/transform: prioritize Strike_R, then Defend_R, then others by reverse priority
                strikes = [
                    c for c in self.game.screen.cards
                    if self._normalize_card_name(c) == "Strike"
                ]
                defends = [
                    c for c in self.game.screen.cards
                    if self._normalize_card_name(c) == "Defend"
                ]
                others = [
                    c
                    for c in self.game.screen.cards
                    if self._normalize_card_name(c) not in ["Strike", "Defend"]
                ]

                # Sort others by reverse priority (worst first)
                others_sorted = self.priorities.get_sorted_cards(others, reverse=True)

                # Combine: strikes first, then defends, then others
                available_cards = strikes + defends + others_sorted
                logging.debug(f"[GRID_SCREEN] Got {len(available_cards)} cards: {self._card_ids_for_tracking(available_cards)}")
            else:
                # Neutral grids such as Duplicator copy/obtain a card; pick the best card, not the worst removal target.
                available_cards = self.priorities.get_sorted_cards(
                    self.game.screen.cards,
                    reverse=False,
                )
                logging.debug(
                    f"[GRID_SCREEN] Neutral good-card grid sorted cards: {self._card_ids_for_tracking(available_cards)}"
                )

            num_cards = self.game.screen.num_cards
            selected_cards = available_cards[:num_cards]
            logging.debug(
                f"[GRID_SCREEN] Returning CardSelectAction with {len(selected_cards)} cards: {self._card_ids_for_tracking(selected_cards)}"
            )
            return CardSelectAction(selected_cards)
        elif self.game.screen_type == ScreenType.HAND_SELECT:
            can_select = self.game.choice_available or (
                hasattr(self.game, "screen")
                and self.game.screen is not None
                and hasattr(self.game.screen, "num_cards")
                and self.game.screen.num_cards > 0
            )
            if not can_select:
                return ProceedAction()
            screen = self.game.screen
            num_required = max(0, self._safe_int(getattr(screen, "num_cards", 0), 0))
            selected_cards = list(getattr(screen, "selected_cards", []) or [])
            num_remaining = max(0, num_required - len(selected_cards))
            if num_remaining == 0:
                return ConfirmAction()
            selected_ids = {id(card) for card in selected_cards}
            available_cards = [
                card for card in screen.cards if id(card) not in selected_ids
            ]
            if not available_cards:
                return ProceedAction()
            # Usually, we don't want to choose the whole hand for a hand select. 3 seems like a good compromise.
            num_cards = min(num_remaining, 3)
            return CardSelectAction(
                self.priorities.get_cards_for_action(
                    self.game.current_action, available_cards, num_cards
                )
            )
        else:
            return ProceedAction()

    def choose_rest_option(self):
        rest_options = self.game.screen.rest_options
        if len(rest_options) > 0 and not self.game.screen.has_rested:
            current_hp = self._safe_float(getattr(self.game, "current_hp", 0), 0.0)
            max_hp = max(self._safe_float(getattr(self.game, "max_hp", 1), 1.0), 1.0)
            floor = self._safe_int(getattr(self.game, "floor", 0), 0)
            act = self._safe_int(getattr(self.game, "act", 1), 1)
            hp_pct = current_hp / max_hp
            is_pre_boss = floor % 17 in (15, 16)
            is_early_act1_low_margin = act == 1 and floor <= 7 and hp_pct < 0.6
            if RestOption.REST in rest_options and (
                hp_pct < 0.5
                or is_early_act1_low_margin
                or (is_pre_boss and hp_pct < 0.8)
            ):
                logging.info(
                    "[REST_GUARD] Forcing REST hp=%s/%s hp_pct=%.1f%% floor=%s pre_boss=%s early_act1_low_margin=%s",
                    current_hp,
                    max_hp,
                    hp_pct * 100,
                    floor,
                    is_pre_boss,
                    is_early_act1_low_margin,
                )
                return RestAction(RestOption.REST)
            if self.map_router is not None and DecisionContext is not None:
                try:
                    context = DecisionContext(self.game)
                    scores = {}
                    if RestOption.REST in rest_options:
                        if hasattr(self.map_router, "_score_rest_option"):
                            scores[RestOption.REST] = self.map_router._score_rest_option(
                                context
                            )
                    if RestOption.SMITH in rest_options:
                        if hasattr(self.map_router, "_score_smith_option"):
                            smith_score = self.map_router._score_smith_option(context)
                        else:
                            smith_score = 0
                        smith_score += self._best_upgrade_score(context)
                        scores[RestOption.SMITH] = smith_score
                    if RestOption.LIFT in rest_options:
                        if hasattr(self.map_router, "_score_lift_option"):
                            scores[RestOption.LIFT] = self.map_router._score_lift_option(
                                context
                            )
                    if RestOption.DIG in rest_options:
                        if hasattr(self.map_router, "_score_dig_option"):
                            scores[RestOption.DIG] = self.map_router._score_dig_option(
                                context
                            )
                    if scores:
                        best_option = max(scores.keys(), key=lambda k: scores[k])
                        logging.info(
                            "[REST] option_scores=%s best=%s",
                            {str(k): scores[k] for k in scores},
                            best_option,
                        )
                        return RestAction(best_option)
                except Exception:
                    pass
            if (
                RestOption.REST in rest_options
                and current_hp < max_hp / 2
            ):
                return RestAction(RestOption.REST)
            elif (
                RestOption.REST in rest_options
                and act != 1
                and floor % 17 == 15
                and current_hp < max_hp * 0.9
            ):
                return RestAction(RestOption.REST)
            elif RestOption.SMITH in rest_options:
                return RestAction(RestOption.SMITH)
            elif RestOption.LIFT in rest_options:
                return RestAction(RestOption.LIFT)
            elif RestOption.DIG in rest_options:
                return RestAction(RestOption.DIG)
            elif (
                RestOption.REST in rest_options
                and current_hp < max_hp
            ):
                return RestAction(RestOption.REST)
            else:
                return ChooseAction(0)
        else:
            return ProceedAction()

    def count_copies_in_deck(self, card):
        count = 0
        target_name = self._normalize_card_name(card)
        for deck_card in self.game.deck:
            if self._normalize_card_name(deck_card) == target_name:
                count += 1
        return count

    def choose_card_reward(self):
        import logging

        logging.info(
            f"[SIMPLE_AGENT_CARD_REWARD] SimpleAgent.choose_card_reward called"
        )
        reward_cards = self.game.screen.cards
        import sys

        can_skip = (
            self.game.screen.can_skip
            if hasattr(self.game.screen, "can_skip")
            else False
        )
        in_combat = self.game.in_combat if hasattr(self.game, "in_combat") else False
        logging.info(
            f"[SIMPLE_AGENT_CARD_REWARD] Floor {self.game.floor if hasattr(self.game, 'floor') else '?'}: {len(reward_cards)} cards, can_skip={can_skip}, in_combat={in_combat}\n"
        )

        for i, card in enumerate(reward_cards):
            count = self.count_copies_in_deck(card)
            needs = (
                self.priorities.needs_more_copies(card, count)
                if can_skip and not in_combat
                else True
            )
            logging.info(
                f"  [{i}] {self._card_id_for_tracking(card)} (copies={count}, needs_more={needs})\n"
            )

        if can_skip and not in_combat:
            pickable_cards = [
                card
                for card in reward_cards
                if self.priorities.needs_more_copies(
                    card, self.count_copies_in_deck(card), self.game.deck
                )
            ]
        else:
            pickable_cards = reward_cards

        if len(pickable_cards) > 0:
            potential_pick = self.priorities.get_best_card(pickable_cards)
            logging.info(
                f"[CARD_REWARD] Choosing: {self._card_id_for_tracking(potential_pick) if potential_pick else 'None'}\n"
            )
            return CardRewardAction(potential_pick)
        elif hasattr(self.game.screen, "can_bowl") and self.game.screen.can_bowl:
            logging.info(f"[CARD_REWARD] Using bowl\n")
            return CardRewardAction(bowl=True)
        else:
            logging.info(f"[CARD_REWARD] Skipping all cards\n")
            self.skipped_cards = True
            return CancelAction()

    def generate_map_route(self):
        context = DecisionContext(self.game) if DecisionContext is not None else None

        # Log current state
        hp_pct = context.player_hp_pct if context else 0
        act = self.game.act if hasattr(self.game, "act") else 1
        floor = self.game.floor if hasattr(self.game, "floor") else 0
        logging.info(
            f"[MAP_ROUTING] Generating route: Act={act}, Floor={floor}, HP={hp_pct:.1%}, Class={self.chosen_class}\n"
        )

        map_height = max(self.game.map.nodes.keys())
        min_reward = -(10**9)
        unreachable_reward = min_reward * 20
        max_elites = 10**6
        no_elite_floor = 10**6
        unreachable_first_elite_floor = -1
        unreachable_combat_count = -(10**6)
        minimize_elites = self._route_should_minimize_elites()
        prioritize_act1_monsters = self._route_should_prioritize_act1_monsters(
            context,
            hp_pct,
            act,
            floor,
        )
        act1_monster_target = self._route_act1_future_monster_target(
            context,
            prioritize_act1_monsters,
        )
        screen = getattr(self.game, "screen", None)
        next_nodes = getattr(screen, "next_nodes", []) or []
        at_act_start = bool(next_nodes) and getattr(next_nodes[0], "y", None) == 0
        current_node = getattr(screen, "current_node", None)
        current_map_node = None
        if (
            not at_act_start
            and current_node is not None
            and getattr(current_node, "y", -1) >= 0
        ):
            current_map_node = self.game.map.get_node(current_node.x, current_node.y)

        start_y = current_map_node.y if current_map_node is not None else 0
        best_rewards = {}
        best_parents = {}
        best_elite_counts = {}
        best_first_elite_floors = {}
        best_act1_monster_counts = {}
        if current_map_node is not None:
            best_rewards[start_y] = {
                node.x: unreachable_reward
                for node in self.game.map.nodes[start_y].values()
            }
            best_rewards[start_y][current_map_node.x] = 0
            best_parents[start_y] = {
                node.x: -1 for node in self.game.map.nodes[start_y].values()
            }
            best_elite_counts[start_y] = {
                node.x: max_elites
                for node in self.game.map.nodes[start_y].values()
            }
            best_elite_counts[start_y][current_map_node.x] = 0
            best_first_elite_floors[start_y] = {
                node.x: unreachable_first_elite_floor
                for node in self.game.map.nodes[start_y].values()
            }
            best_first_elite_floors[start_y][current_map_node.x] = no_elite_floor
            best_act1_monster_counts[start_y] = {
                node.x: unreachable_combat_count
                for node in self.game.map.nodes[start_y].values()
            }
            best_act1_monster_counts[start_y][current_map_node.x] = 0
            logging.info(
                "[MAP_ROUTING] Replan seed: current_node=(%s,%s) symbol=%s\n",
                current_map_node.x,
                current_map_node.y,
                current_map_node.symbol,
            )
        else:
            best_rewards[0] = {
                node.x: self._calculate_map_node_priority(node, context)
                for node in self.game.map.nodes[0].values()
            }
            best_parents[0] = {
                node.x: 0 for node in self.game.map.nodes[0].values()
            }
            best_elite_counts[0] = {
                node.x: self._future_elite_count(node, minimize_elites)
                for node in self.game.map.nodes[0].values()
            }
            best_first_elite_floors[0] = {
                node.x: self._first_elite_floor(
                    node,
                    minimize_elites,
                    no_elite_floor,
                )
                for node in self.game.map.nodes[0].values()
            }
            best_act1_monster_counts[0] = {
                node.x: self._future_act1_monster_count(
                    node,
                    prioritize_act1_monsters,
                )
                for node in self.game.map.nodes[0].values()
            }

        for y in range(start_y, map_height):
            best_rewards[y + 1] = {
                node.x: unreachable_reward
                for node in self.game.map.nodes[y + 1].values()
            }
            best_parents[y + 1] = {
                node.x: -1 for node in self.game.map.nodes[y + 1].values()
            }
            best_elite_counts[y + 1] = {
                node.x: max_elites
                for node in self.game.map.nodes[y + 1].values()
            }
            best_first_elite_floors[y + 1] = {
                node.x: unreachable_first_elite_floor
                for node in self.game.map.nodes[y + 1].values()
            }
            best_act1_monster_counts[y + 1] = {
                node.x: unreachable_combat_count
                for node in self.game.map.nodes[y + 1].values()
            }
            for x in best_rewards[y]:
                node = self.game.map.get_node(x, y)
                best_node_reward = best_rewards[y][x]
                if node is None or best_node_reward <= unreachable_reward:
                    continue
                for child in node.children:
                    child_priority = self._calculate_map_node_priority(child, context)
                    if (
                        prioritize_act1_monsters
                        and act1_monster_target > 0
                        and getattr(child, "symbol", None) == "M"
                        and best_act1_monster_counts[y][x] >= act1_monster_target
                    ):
                        child_priority -= 160
                    test_child_reward = best_node_reward + child_priority
                    elite_count = (
                        best_elite_counts[y][x]
                        + self._future_elite_count(child, minimize_elites)
                    )
                    first_elite_floor = self._updated_first_elite_floor(
                        best_first_elite_floors[y][x],
                        child,
                        minimize_elites,
                        no_elite_floor,
                    )
                    act1_monster_count = (
                        best_act1_monster_counts[y][x]
                        + self._future_act1_monster_count(
                            child,
                            prioritize_act1_monsters,
                        )
                    )
                    if self._is_better_map_route(
                        reward=test_child_reward,
                        elite_count=elite_count,
                        first_elite_floor=first_elite_floor,
                        act1_monster_count=act1_monster_count,
                        current_reward=best_rewards[y + 1][child.x],
                        current_elite_count=best_elite_counts[y + 1][child.x],
                        current_first_elite_floor=best_first_elite_floors[y + 1][
                            child.x
                        ],
                        current_act1_monster_count=best_act1_monster_counts[y + 1][
                            child.x
                        ],
                        minimize_elites=minimize_elites,
                        prioritize_act1_monsters=prioritize_act1_monsters,
                        act1_monster_target=act1_monster_target,
                    ):
                        best_rewards[y + 1][child.x] = test_child_reward
                        best_parents[y + 1][child.x] = node.x
                        best_elite_counts[y + 1][child.x] = elite_count
                        best_first_elite_floors[y + 1][child.x] = first_elite_floor
                        best_act1_monster_counts[y + 1][child.x] = act1_monster_count

                    # Log node evaluation (first few floors)
                    if y < 5:
                        logging.info(
                            f"[MAP_ROUTING] Floor {y + 1}: node({child.x},{child.y}) symbol={child.symbol} priority={child_priority} total_reward={test_child_reward}\n"
                        )

        best_path = [0] * (map_height + 1)
        reachable_final_nodes = [
            x
            for x, reward in best_rewards[map_height].items()
            if reward > unreachable_reward
        ]
        final_candidates = reachable_final_nodes or list(best_rewards[map_height].keys())
        if minimize_elites:
            best_path[map_height] = min(
                final_candidates,
                key=lambda x: (
                    best_elite_counts[map_height].get(x, max_elites),
                    -best_first_elite_floors[map_height].get(
                        x,
                        unreachable_first_elite_floor,
                    ),
                    -self._route_capped_act1_monster_count(
                        best_act1_monster_counts[map_height].get(
                            x,
                            unreachable_combat_count,
                        ),
                        act1_monster_target,
                    ) if prioritize_act1_monsters else 0,
                    -best_rewards[map_height][x],
                ),
            )
        elif prioritize_act1_monsters:
            best_path[map_height] = max(
                final_candidates,
                key=lambda x: (
                    self._route_capped_act1_monster_count(
                        best_act1_monster_counts[map_height].get(
                            x,
                            unreachable_combat_count,
                        ),
                        act1_monster_target,
                    ),
                    best_rewards[map_height][x],
                ),
            )
        else:
            best_path[map_height] = max(
                final_candidates, key=lambda x: best_rewards[map_height][x]
            )
        for y in range(map_height, start_y, -1):
            best_path[y - 1] = best_parents[y][best_path[y]]
        if current_map_node is not None:
            best_path[start_y] = current_map_node.x
        self.map_route = best_path

        # Log chosen path
        path_summary = []
        for y in range(len(best_path)):
            node = self.game.map.get_node(best_path[y], y)
            if node:
                path_summary.append(f"{y}:{node.symbol}")
        logging.info(f"[MAP_ROUTING] Chosen path: {' -> '.join(path_summary)}\n")
        self._last_route_hp_pct = hp_pct
        self._last_route_floor = floor

    def _route_should_minimize_elites(self):
        if str(self.elite_mode or "").lower() == "conservative":
            return True
        return str(getattr(self.map_router, "elite_mode", "")).lower() == "conservative"

    def _route_should_prioritize_act1_monsters(self, context, hp_pct, act, floor):
        if context is None or self.map_router is None:
            return False
        if self.chosen_class != PlayerClass.IRONCLAD:
            return False
        if self._safe_int(act, 0) != 1:
            return False
        if self._safe_float(hp_pct, 0.0) < 0.55:
            return False
        needs_rewards = getattr(
            self.map_router,
            "_act_1_needs_combat_rewards",
            None,
        )
        if needs_rewards is None:
            return False
        return bool(needs_rewards(context, self._safe_int(floor, 0), hp_pct))

    def _route_act1_future_monster_target(self, context, prioritize_act1_monsters):
        if not prioritize_act1_monsters or context is None or self.map_router is None:
            return 0
        game = getattr(context, "game", None)
        deck = list(getattr(game, "deck", []) or [])
        if not deck:
            return 0

        card_name = getattr(self.map_router, "_card_name", None)
        if callable(card_name):
            card_names = [card_name(card) for card in deck]
        else:
            card_names = [
                getattr(card, "name", getattr(card, "card_id", "")) for card in deck
            ]
        premium_attacks = getattr(self.map_router, "ACT1_PREMIUM_ATTACKS", set())
        strong_blocks = getattr(self.map_router, "ACT1_STRONG_BLOCKS", set())
        premium_count = sum(1 for name in card_names if name in premium_attacks)
        strong_block_count = sum(1 for name in card_names if name in strong_blocks)
        floor = self._safe_int(getattr(context, "floor", 0), 0)

        if floor <= 6:
            future_needed = max(12 - len(deck), 2 - premium_count)
        elif floor <= 12:
            future_needed = max(
                14 - len(deck),
                3 - premium_count,
                5 - (premium_count + strong_block_count),
            )
        else:
            future_needed = max(15 - len(deck), 4 - premium_count)
        return max(1, min(3, future_needed))

    @staticmethod
    def _future_elite_count(node, minimize_elites):
        if not minimize_elites:
            return 0
        return 1 if getattr(node, "symbol", None) == "E" else 0

    @staticmethod
    def _first_elite_floor(node, minimize_elites, no_elite_floor):
        if not minimize_elites:
            return no_elite_floor
        if getattr(node, "symbol", None) == "E":
            return getattr(node, "y", 0)
        return no_elite_floor

    @staticmethod
    def _updated_first_elite_floor(
        current_first_elite_floor,
        node,
        minimize_elites,
        no_elite_floor,
    ):
        if not minimize_elites:
            return no_elite_floor
        if current_first_elite_floor != no_elite_floor:
            return current_first_elite_floor
        return SimpleAgent._first_elite_floor(node, minimize_elites, no_elite_floor)

    @staticmethod
    def _future_act1_monster_count(node, prioritize_act1_monsters):
        if not prioritize_act1_monsters:
            return 0
        if getattr(node, "symbol", None) != "M":
            return 0
        return 1 if getattr(node, "y", 0) <= 7 else 0

    @staticmethod
    def _route_capped_act1_monster_count(count, target):
        if target <= 0:
            return count
        return min(count, target)

    @staticmethod
    def _is_better_map_route(
        reward,
        elite_count,
        first_elite_floor,
        act1_monster_count,
        current_reward,
        current_elite_count,
        current_first_elite_floor,
        current_act1_monster_count,
        minimize_elites,
        prioritize_act1_monsters,
        act1_monster_target=0,
    ):
        if minimize_elites:
            if elite_count != current_elite_count:
                return elite_count < current_elite_count
            if elite_count > 0 and first_elite_floor != current_first_elite_floor:
                return first_elite_floor > current_first_elite_floor
        if prioritize_act1_monsters:
            capped_count = SimpleAgent._route_capped_act1_monster_count(
                act1_monster_count,
                act1_monster_target,
            )
            current_capped_count = SimpleAgent._route_capped_act1_monster_count(
                current_act1_monster_count,
                act1_monster_target,
            )
            if capped_count != current_capped_count:
                return capped_count > current_capped_count
        return reward > current_reward

    def _calculate_map_node_priority(self, node, context):
        if self.map_router is None or context is None:
            node_rewards = self.priorities.MAP_NODE_PRIORITIES.get(self.game.act, {})
            return node_rewards.get(node.symbol, 0)
        context.floor = node.y + 1
        return self.map_router.calculate_node_priority(node, context)

    def make_map_choice(self):
        if (
            len(self.game.screen.next_nodes) > 0
            and self.game.screen.next_nodes[0].y == 0
        ):
            self.generate_map_route()
            self.game.screen.current_node.y = -1
        else:
            context = (
                DecisionContext(self.game) if DecisionContext is not None else None
            )
            hp_pct = context.player_hp_pct if context else 0
            if (
                self._last_route_hp_pct is None
                or (self._last_route_hp_pct - hp_pct) >= self._map_replan_hp_drop
            ):
                drop = (
                    (self._last_route_hp_pct - hp_pct)
                    if self._last_route_hp_pct is not None
                    else None
                )
                drop_str = f"{drop:.1%}" if drop is not None else "n/a"
                logging.info(
                    "[MAP_ROUTING] Replan triggered: last_hp=%s current_hp=%.1f%% drop=%s threshold=%.1f%%\n",
                    f"{self._last_route_hp_pct:.1%}"
                    if self._last_route_hp_pct is not None
                    else "n/a",
                    hp_pct * 100,
                    drop_str,
                    self._map_replan_hp_drop * 100,
                )
                self.generate_map_route()
        if self.game.screen.boss_available:
            return ChooseMapBossAction()
        chosen_x = self.map_route[self.game.screen.current_node.y + 1]
        for choice in self.game.screen.next_nodes:
            if choice.x == chosen_x:
                return ChooseMapNodeAction(choice)
        # This should never happen
        return ChooseAction(0)


class TurnPlanSignature:
    """
    Signature of turn state for cache validation and replan triggering.

    Tracks the game state when a plan was created to detect if the plan
    becomes invalid due to card draws, monster deaths, player damage, etc.
    """

    def __init__(self, game):
        """Create signature from current game state."""
        # Track hand cards by UUID to detect draws/exhausts
        self.hand_cards = tuple(
            self._card_signature(c)
            for c in game.hand
        )

        player = getattr(game, "player", None)

        # Track player state that can change whether the cached plan is safe.
        self.player_hp = getattr(game, "current_hp", getattr(player, "current_hp", None))
        self.player_block = getattr(player, "block", getattr(game, "block", 0))
        self.player_powers = self._powers_signature(getattr(player, "powers", None))

        # Track available energy
        self.energy = getattr(player, "energy", getattr(game, "energy", 3))

        # Track potion slots because cached plans can contain PotionAction objects.
        raw_potions = getattr(game, "potions", None)
        potions = raw_potions if raw_potions is not None else game_real_potions(game)
        self.potion_signature = self._potion_signature(potions)

        # Track monster states
        if hasattr(game, "monsters") and game.monsters:
            self.monster_signature = tuple(
                (
                    getattr(m, "monster_id", None),
                    getattr(m, "name", None),
                    m.current_hp,
                    m.block if hasattr(m, "block") else 0,
                    str(m.intent) if hasattr(m, "intent") else None,
                    getattr(m, "move_adjusted_damage", None),
                    getattr(m, "move_hits", None),
                    self._powers_signature(getattr(m, "powers", None)),
                    m.is_gone if hasattr(m, "is_gone") else True,
                    m.half_dead if hasattr(m, "half_dead") else False,
                )
                for m in game.monsters
            )
        else:
            self.monster_signature = tuple()

        # Flags for random events that invalidate plan
        self.has_drawn_cards = False  # Set to True if draw events occur
        self.has_random_effects = False  # Set for random targeting/shuffle

    @staticmethod
    def _card_signature(card):
        card_identity = None
        for attr in ("uuid", "card_id", "name"):
            value = getattr(card, attr, None)
            if value:
                card_identity = value
                break
        if card_identity is None:
            card_identity = id(card)
        return (
            card_identity,
            card_upgrade_count(card),
            getattr(card, "cost", None),
            getattr(card, "cost_for_turn", getattr(card, "cost", None)),
            getattr(card, "is_playable", None),
        )

    @staticmethod
    def _powers_signature(powers):
        signatures = [power_signature(power) for power in powers or []]
        return tuple(sorted(signatures, key=TurnPlanSignature._power_signature_sort_key))

    @staticmethod
    def _power_signature_sort_key(signature):
        identifier, amount = signature
        return (
            identifier is None,
            str(identifier) if identifier is not None else "",
            amount is None,
            str(amount) if amount is not None else "",
        )

    @staticmethod
    def _potion_signature(potions):
        potion_signatures = []
        for index, potion in enumerate(potions or []):
            potion_identity = potion_id(potion)
            potion_signatures.append(
                (
                    index,
                    potion_identity,
                    getattr(potion, "name", None),
                    getattr(potion, "can_use", None),
                    getattr(potion, "can_discard", None),
                    getattr(potion, "requires_target", None),
                    getattr(potion, "effect_type", None),
                    getattr(potion, "effect_value", None),
                    getattr(potion, "target_type", None),
                )
            )
        return tuple(potion_signatures)

    def __eq__(self, other):
        """Check if two signatures are equal."""
        if not isinstance(other, TurnPlanSignature):
            return False
        return (
            self.hand_cards == other.hand_cards
            and self.player_hp == other.player_hp
            and self.player_block == other.player_block
            and self.player_powers == other.player_powers
            and self.energy == other.energy
            and self.potion_signature == other.potion_signature
            and self.monster_signature == other.monster_signature
            and self.has_drawn_cards == other.has_drawn_cards
            and self.has_random_effects == other.has_random_effects
        )

    def __hash__(self):
        """Make signature hashable for use in sets/dicts."""
        return hash(
            (
                self.hand_cards,
                self.player_hp,
                self.player_block,
                self.player_powers,
                self.energy,
                self.potion_signature,
                self.monster_signature,
                self.has_drawn_cards,
                self.has_random_effects,
            )
        )


class OptimizedAgent(SimpleAgent):
    """
    Enhanced agent with modular decision system.

    This agent inherits from SimpleAgent for backward compatibility but uses
    advanced heuristics for decision making. It features:
    - Synergy-based card evaluation
    - Beam search combat planning
    - Adaptive strategy based on deck archetype
    - Context-aware decision making
    - Smart replan triggering for dynamic game states

    Usage:
        agent = OptimizedAgent(chosen_class=PlayerClass.THE_SILENT)
    """

    def __init__(
        self,
        chosen_class=PlayerClass.THE_SILENT,
        use_optimized_combat=True,
        use_optimized_card_selection=True,
        elite_mode=None,
    ):
        """
        Initialize OptimizedAgent.

        Args:
            chosen_class: Player class to use
            use_optimized_combat: Use enhanced combat planning (default: True)
            use_optimized_card_selection: Use synergy-based card evaluation (default: True)
            elite_mode: Elite routing mode ("conservative" or "aggressive", default: None)
        """
        # Initialize parent class
        super().__init__(chosen_class, elite_mode=elite_mode)

        # Check if optimized components are available
        if not OPTIMIZED_AI_AVAILABLE:
            # Silent fallback - no print statements
            use_optimized_combat = False
            use_optimized_card_selection = False

        # Configuration flags
        self.use_optimized_combat = use_optimized_combat
        self.use_optimized_card_selection = use_optimized_card_selection

        # Initialize game tracker
        if GameTracker is not None:
            self.game_tracker = GameTracker()
            self.game_tracker.player_class = str(chosen_class).replace(
                "PlayerClass.", ""
            )
        else:
            self.game_tracker = None
        self._in_combat = False
        self._last_relics = set()
        self._last_turn = 0

        # Initialize decision components if available
        if OPTIMIZED_AI_AVAILABLE:
            player_class_str = str(chosen_class).replace("PlayerClass.", "")

            # Use class-specific components for Ironclad
            if player_class_str == "IRONCLAD":
                from spirecomm.ai.heuristics.ironclad_evaluator import (
                    IroncladCardEvaluator,
                )
                from spirecomm.ai.heuristics.ironclad_combat import (
                    IroncladCombatPlanner,
                )
                from spirecomm.ai.heuristics.ironclad_archetype import (
                    IroncladArchetypeManager,
                )
                from spirecomm.ai.heuristics.ironclad_deck import IroncladDeckStrategy
                from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter

                self.card_evaluator = IroncladCardEvaluator(
                    player_class=player_class_str
                )
                self.combat_planner = IroncladCombatPlanner(
                    card_evaluator=self.card_evaluator
                )
                self.archetype_manager = IroncladArchetypeManager()
                self.deck_strategy = IroncladDeckStrategy()
                self.map_router = AdaptiveMapRouter(player_class=player_class_str, elite_mode=self.elite_mode)
                self.deck_analyzer = DeckAnalyzer()  # Keep for compatibility
            else:
                # Use generic components for other classes
                self.card_evaluator = SynergyCardEvaluator(
                    player_class=player_class_str
                )
                self.combat_planner = HeuristicCombatPlanner(
                    card_evaluator=self.card_evaluator, player_class=player_class_str
                )
                self.deck_analyzer = DeckAnalyzer()
                self.archetype_manager = None
                self.deck_strategy = None
                # All classes get map router
                from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter

                self.map_router = AdaptiveMapRouter(player_class=player_class_str, elite_mode=self.elite_mode)

            # Track decision history for analysis
            self.decision_history = []

            # === 新增：存储规划的动作序列 ===
            self.current_action_sequence = []
            self.current_action_index = 0

            # === 新增：存储当前计划的签名用于缓存失效检测 ===
            self.current_plan_signature = None

            # 统计重新规划次数（用于调优）
            self.replan_count_this_turn = 0
        else:
            self.card_evaluator = None
            self.combat_planner = None
            self.deck_analyzer = None
            self.archetype_manager = None
            self.deck_strategy = None
            self.map_router = None
            self.decision_history = []
            self.current_action_sequence = []
            self.current_action_index = 0
            self.current_plan_signature = None
            self.replan_count_this_turn = 0

    def get_play_card_action(self):
        """
        Override with optimized combat logic if enabled.

        Returns:
            PlayCardAction or EndTurnAction
        """
        game_id = getattr(self.game, "game_id", None)

        def _fallback_snapshot():
            try:
                hand_ids = self._card_ids_for_tracking(self.game.hand)
                monsters = []
                for m in self.game.monsters:
                    if m.is_gone or m.half_dead:
                        continue
                    intent = str(m.intent) if hasattr(m, "intent") else "UNKNOWN"
                    monsters.append(f"{m.name}:{m.current_hp}/{m.max_hp}:{intent}")
                return (
                    f"hp={self.game.current_hp}/{self.game.max_hp} "
                    f"block={self.game.player.block} "
                    f"energy={self.game.energy} "
                    f"hand={hand_ids} "
                    f"monsters={monsters}"
                )
            except Exception:
                return "snapshot=unavailable"

        try:
            if (
                self.use_optimized_combat
                and self.combat_planner
                and OPTIMIZED_AI_AVAILABLE
            ):
                return self._get_optimized_play_card_action()
            else:
                # Log why we're falling back
                if not self.use_optimized_combat:
                    logger.warning(
                        "[OPTIMIZED_AI] game_id=%s use_optimized_combat is False %s",
                        game_id,
                        _fallback_snapshot(),
                    )
                elif not self.combat_planner:
                    logger.warning(
                        "[OPTIMIZED_AI] game_id=%s combat_planner is None %s",
                        game_id,
                        _fallback_snapshot(),
                    )
                elif not OPTIMIZED_AI_AVAILABLE:
                    logger.warning(
                        "[OPTIMIZED_AI] game_id=%s OPTIMIZED_AI_AVAILABLE is False %s",
                        game_id,
                        _fallback_snapshot(),
                    )
                # Fall back to SimpleAgent logic
                return super().get_play_card_action()
        except Exception as e:
            # On error, log and fall back to simple logic
            import sys

            print(f"Error in optimized combat: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            logger.exception(
                "[OPTIMIZED_AI] game_id=%s Exception in optimized combat %s",
                game_id,
                _fallback_snapshot(),
            )
            return super().get_play_card_action()

    def _get_optimized_play_card_action(self):
        """
        Use optimized combat planning with proper sequence execution.

        关键改变：存储并执行完整序列，不只是第一张卡

        Returns:
            PlayCardAction or EndTurnAction
        """
        if not self.game.play_available:
            return EndTurnAction()

        game_id = getattr(self.game, "game_id", None)
        try:
            # === 新增：检查是否需要重新规划 ===
            # 创建当前游戏状态的签名
            current_signature = TurnPlanSignature(self.game)

            # 如果有待执行的序列，检查是否仍然有效
            if self.current_action_sequence and self.current_action_index < len(
                self.current_action_sequence
            ):
                # Continue planned card sequences when the next planned action is
                # still available. Playing earlier cards changes hand/energy by
                # design, so signature mismatch alone cannot invalidate a plan.
                action = self.current_action_sequence[self.current_action_index]
                if self._cached_sequence_action_available(action):
                    self.current_action_index += 1
                    return action

                # 检查缓存是否失效
                if self.should_replan(current_signature):
                    # 缓存失效 - 需要重新规划
                    self.replan_count_this_turn += 1
                    self.current_action_sequence = []
                    self.current_action_index = 0
                else:
                    # 动作不再可执行，重置序列
                    self.current_action_sequence = []
                    self.current_action_index = 0

            # 规划新序列（首次规划或缓存失效后）
            context = DecisionContext(self.game)

            # === Enhanced combat mode selection using Wiki monster data ===
            # Import combat mode selector
            from spirecomm.ai.heuristics.simulation import (
                select_combat_mode_with_monster_data,
                CombatMode,
            )
            from spirecomm.ai.decision.base import ThreatCategory

            # Select combat mode based on enhanced monster analysis
            # This uses Wiki data to detect summoners, phase changes, hibernation, etc.
            try:
                combat_mode = select_combat_mode_with_monster_data(context)
            except Exception as e:
                # Fallback to original method if enhanced version fails
                logger.warning(
                    f"Enhanced combat mode selection failed: {e}, falling back to basic mode"
                )
                from spirecomm.ai.heuristics.simulation import select_combat_mode

                combat_mode = select_combat_mode(context.threat_category)

            # Check if we need to recreate combat planner (mode changed)
            if (
                not hasattr(self, "_current_combat_mode")
                or self._current_combat_mode != combat_mode
            ):
                # Combat mode changed, recreate planner with new mode
                # IMPORTANT: Preserve class-specific planner (e.g., IroncladCombatPlanner)
                player_class_str = getattr(self, "player_class", "IRONCLAD")
                if player_class_str == "IRONCLAD" and OPTIMIZED_AI_AVAILABLE:
                    from spirecomm.ai.heuristics.ironclad_combat import (
                        IroncladCombatPlanner,
                    )

                    self.combat_planner = IroncladCombatPlanner(
                        card_evaluator=self.card_evaluator, combat_mode=combat_mode
                    )
                else:
                    self.combat_planner = HeuristicCombatPlanner(
                        card_evaluator=self.card_evaluator,
                        player_class=player_class_str,
                        act=context.act,
                        combat_mode=combat_mode,
                    )
                self._current_combat_mode = combat_mode

            action_sequence = self.combat_planner.plan_turn(context)

            if action_sequence:
                # 存储序列用于执行
                self.current_action_sequence = action_sequence
                self.current_action_index = 0

                # === 新增：保存当前计划签名 ===
                self.current_plan_signature = current_signature

                # 计算置信度
                confidence = 0.5  # 默认值
                if self.combat_planner and hasattr(
                    self.combat_planner, "get_confidence"
                ):
                    try:
                        confidence = self.combat_planner.get_confidence(context)
                    except:
                        pass

                # 记录决策用于分析
                self.decision_history.append(
                    {
                        "type": "combat",
                        "sequence": action_sequence,
                        "turn": context.turn,
                        "floor": context.floor,
                        "confidence": confidence,
                    }
                )

                # 记录到 game_tracker
                if self.game_tracker:
                    self.game_tracker.record_decision(
                        decision_type="combat",
                        confidence=confidence,
                        used_fallback=False,
                    )

                # Record potion usage when beam search selects a potion action.
                if self.game_tracker and action_sequence:
                    try:
                        from spirecomm.communication.action import PotionAction

                        if isinstance(action_sequence[0], PotionAction):
                            self.game_tracker.record_potion_use()
                    except Exception:
                        pass

                # 返回第一个动作
                self.current_action_index = 1
                return action_sequence[0]

            # 没有规划的动作 - 结束回合
            self.current_action_sequence = []
            return EndTurnAction()

        except Exception as e:
            import sys

            print(f"Error in _get_optimized_play_card_action: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            logger.exception(
                "[OPTIMIZED_AI] game_id=%s Exception in _get_optimized_play_card_action",
                game_id,
            )
            self.current_action_sequence = []
            return super().get_play_card_action()

    def _cached_sequence_action_available(self, action):
        if isinstance(action, PlayCardAction):
            hand = getattr(self.game, "hand", []) or []
            card = getattr(action, "card", None)
            card_uuid = getattr(card, "uuid", None) if card is not None else None
            if card_uuid is not None:
                for idx, hand_card in enumerate(hand):
                    if getattr(hand_card, "uuid", None) == card_uuid:
                        action.card = hand_card
                        action.card_index = idx
                        return True
                return False

            if 0 <= getattr(action, "card_index", -1) < len(hand):
                return True

            if card is not None:
                try:
                    action.card_index = hand.index(card)
                    return True
                except (ValueError, AttributeError):
                    return False

            return False

        if isinstance(action, PotionAction):
            potion = getattr(action, "potion", None)
            if potion is None:
                return getattr(action, "potion_index", -1) >= 0
            potions = getattr(self.game, "potions", None)
            if potions is None:
                get_real_potions = getattr(self.game, "get_real_potions", None)
                potions = get_real_potions() if callable(get_real_potions) else []
            return potion in (potions or [])

        return True

    def should_replan(self, current_signature):
        """
        Check if the cached plan is still valid.

        Returns True if any of the following conditions are met:
        - No previous signature (first time planning this turn)
        - Any signed combat state changed (hand, player state, energy, potions, monsters)
        - Random effects occurred (shuffle, random targeting)

        Args:
            current_signature: Current TurnPlanSignature

        Returns:
            True if should replan, False otherwise
        """
        # No previous signature - need to plan
        if self.current_plan_signature is None:
            return True

        # Check for any signed state mismatch. Keep this centralized so adding
        # fields to TurnPlanSignature automatically invalidates stale plans.
        if self.current_plan_signature != current_signature:
            return True

        # Check for random events
        if current_signature.has_drawn_cards or current_signature.has_random_effects:
            # Random effects invalidate the plan
            return True

        # Signature matches - cached plan is still valid
        return False

    def get_next_action_in_game(self, game_state):
        """
        Override to detect turn changes, combat events, and track statistics.

        Args:
            game_state: Current game state
        """
        # Attach stable game_id for logging correlation
        if self.game_tracker:
            try:
                game_state.game_id = int(self.game_tracker.game_start_time.timestamp())
            except Exception:
                pass

        # 检测回合变化
        if hasattr(game_state, "turn") and hasattr(self.game, "turn"):
            if game_state.turn != self.game.turn:
                # 新回合 - 重置动作序列和签名
                self.current_action_sequence = []
                self.current_action_index = 0
                self.current_plan_signature = None
                self.replan_count_this_turn = 0

        # Track game statistics if available
        if self.game_tracker and hasattr(game_state, "in_combat"):
            try:
                # 检测战斗状态变化
                current_in_combat = game_state.in_combat

                if current_in_combat and not self._in_combat:
                    # 战斗开始
                    room_type = "monster"
                    if hasattr(game_state, "room_type"):
                        rt = str(game_state.room_type)
                        if "Elite" in rt:
                            room_type = "elite"
                        elif "Boss" in rt:
                            room_type = "boss"

                    self.game_tracker.start_combat(
                        floor=game_state.floor if hasattr(game_state, "floor") else 0,
                        act=game_state.act if hasattr(game_state, "act") else 1,
                        room_type=room_type,
                        start_turn=game_state.turn
                        if hasattr(game_state, "turn")
                        else 0,
                        current_hp=game_state.current_hp
                        if hasattr(game_state, "current_hp")
                        else None,
                    )
                    self._in_combat = True
                elif not current_in_combat and self._in_combat:
                    self.game_tracker.end_combat(
                        hp_remaining=game_state.current_hp
                        if hasattr(game_state, "current_hp")
                        else 80,
                        max_hp=game_state.max_hp
                        if hasattr(game_state, "max_hp")
                        else 80,
                        end_turn=game_state.turn
                        if hasattr(game_state, "turn")
                        else None,
                    )
                    self._in_combat = False

                # 检测遗物获得
                if hasattr(game_state, "relics"):
                    current_relics = set(
                        r.relic_id if hasattr(r, "relic_id") else str(r)
                        for r in game_state.relics
                    )
                    new_relics = current_relics - self._last_relics
                    for relic_id in new_relics:
                        self.game_tracker.record_relic(relic_id)
                    self._last_relics = current_relics
            except Exception as e:
                # Silently fail on tracking errors to not break the game
                import sys

                print(f"Error in game tracking: {e}", file=sys.stderr)

        # 更新游戏状态
        self.game = game_state

        # 调用父类方法
        return super().get_next_action_in_game(game_state)

    def _track_game_state(self, game_state):
        """
        Track game state statistics without making decisions.

        This method is called by CombatRLAgent to ensure statistics
        are collected even when RL makes the decisions.

        Args:
            game_state: Current game state
        """
        if not self.game_tracker or not hasattr(game_state, "in_combat"):
            return

        try:
            # 检测战斗状态变化
            current_in_combat = game_state.in_combat

            if current_in_combat and not self._in_combat:
                # 战斗开始
                room_type = "monster"
                if hasattr(game_state, "room_type"):
                    rt = str(game_state.room_type)
                    if "Elite" in rt:
                        room_type = "elite"
                    elif "Boss" in rt:
                        room_type = "boss"

                import logging
                logging.info(f"[TRACKING] Starting combat: floor={game_state.floor if hasattr(game_state, 'floor') else '?'}, type={room_type}")
                self.game_tracker.start_combat(
                    floor=game_state.floor if hasattr(game_state, "floor") else 0,
                    act=game_state.act if hasattr(game_state, "act") else 1,
                    room_type=room_type,
                    start_turn=game_state.turn
                    if hasattr(game_state, "turn")
                    else 0,
                    current_hp=game_state.current_hp
                    if hasattr(game_state, "current_hp")
                    else None,
                )
                self._in_combat = True
            elif not current_in_combat and self._in_combat:
                self.game_tracker.end_combat(
                    hp_remaining=game_state.current_hp
                    if hasattr(game_state, "current_hp")
                    else 80,
                    max_hp=game_state.max_hp
                    if hasattr(game_state, "max_hp")
                    else 80,
                    end_turn=game_state.turn
                    if hasattr(game_state, "turn")
                    else None,
                )
                self._in_combat = False

            # 检测遗物获得
            if hasattr(game_state, "relics"):
                current_relics = set(
                    r.relic_id if hasattr(r, "relic_id") else str(r)
                    for r in game_state.relics
                )
                new_relics = current_relics - self._last_relics
                for relic_id in new_relics:
                    self.game_tracker.record_relic(relic_id)
                self._last_relics = current_relics
        except Exception as e:
            # Silently fail on tracking errors to not break the game
            import sys
            print(f"Error in game tracking: {e}", file=sys.stderr)

    def _is_generated_combat_card_choice(self, reward_cards=None):
        screen = getattr(self.game, "screen", None)
        if screen is None:
            return False
        cards = reward_cards
        if cards is None:
            cards = getattr(screen, "cards", []) or []
        if not cards:
            return False
        if getattr(screen, "can_skip", False) or getattr(screen, "can_bowl", False):
            return False

        live_monsters = [
            monster
            for monster in (getattr(self.game, "monsters", []) or [])
            if self._is_live_monster(monster)
        ]
        if not live_monsters:
            return False

        room_type = str(getattr(self.game, "room_type", ""))
        return bool(getattr(self.game, "in_combat", False)) or "Monster" in room_type

    def choose_card_reward(self):
        """
        Override with optimized card selection if enabled.
        Always records card choices to game_tracker for statistics.

        Returns:
            CardRewardAction or CancelAction
        """
        import logging

        # Get reward cards before they're modified
        reward_cards = (
            self.game.screen.cards
            if hasattr(self.game, "screen") and hasattr(self.game.screen, "cards")
            else []
        )

        # LOG: Entry point
        logging.info(f"[CARD_REWARD_DEBUG] choose_card_reward called")
        logging.info(f"[CARD_REWARD_DEBUG] reward_cards count: {len(reward_cards)}")
        for i, card in enumerate(reward_cards):
            logging.info(
                f"[CARD_REWARD_DEBUG]   Card {i}: {self._card_id_for_tracking(card)} (name={getattr(card, 'name', '')})"
            )
        combat_generated_choice = self._is_generated_combat_card_choice(reward_cards)
        if combat_generated_choice:
            logging.info(
                "[CARD_REWARD_DEBUG] Treating CARD_REWARD as generated combat card choice; "
                "deck reward tracking disabled"
            )

        # Check conditions
        use_optimized = (
            self.use_optimized_card_selection
            and self.card_evaluator
            and OPTIMIZED_AI_AVAILABLE
        )
        logging.info(
            f"[CARD_REWARD_DEBUG] use_optimized_card_selection: {self.use_optimized_card_selection}"
        )
        logging.info(
            f"[CARD_REWARD_DEBUG] card_evaluator exists: {self.card_evaluator is not None}"
        )
        logging.info(
            f"[CARD_REWARD_DEBUG] OPTIMIZED_AI_AVAILABLE: {OPTIMIZED_AI_AVAILABLE}"
        )
        logging.info(f"[CARD_REWARD_DEBUG] Will use optimized path: {use_optimized}")

        # Get action from parent (either optimized or simple logic)
        original_game_tracker = self.game_tracker
        if combat_generated_choice:
            self.game_tracker = None
        if use_optimized:
            logging.info(f"[CARD_REWARD_DEBUG] Taking OPTIMIZED path")
            try:
                action = self._choose_card_reward_optimized()
            finally:
                self.game_tracker = original_game_tracker
        else:
            logging.info(f"[CARD_REWARD_DEBUG] Taking SIMPLE path (fallback)")
            try:
                action = super().choose_card_reward()
            finally:
                self.game_tracker = original_game_tracker

        # LOG: Action result
        logging.info(f"[CARD_REWARD_DEBUG] Action type: {type(action).__name__}")
        if isinstance(action, CardRewardAction):
            logging.info(f"[CARD_REWARD_DEBUG] Action name: {action.name}")
        logging.info(f"[CARD_REWARD_DEBUG] Action repr: {repr(action)}")

        if combat_generated_choice:
            logging.info(
                "[CARD_REWARD_DEBUG] Generated combat card choice selected; "
                "skipping game_tracker card reward recording"
            )
            return action

        # Record the choice for statistics
        if self.game_tracker:
            logging.info(f"[CARD_REWARD_DEBUG] game_tracker exists: True")
            card_count_before = (
                len(self.game_tracker.cards_obtained)
                if self.game_tracker.cards_obtained
                else 0
            )
            logging.info(
                f"[CARD_REWARD_DEBUG] Current cards_obtained count (before): {card_count_before}"
            )
        else:
            logging.info(
                f"[CARD_REWARD_DEBUG] game_tracker exists: False - SKIPPING RECORDING"
            )

        if self.game_tracker and reward_cards:
            # Check cards_obtained count before and after to detect if optimized path already recorded
            card_count_before = (
                len(self.game_tracker.cards_obtained)
                if self.game_tracker.cards_obtained
                else 0
            )
            logging.info(
                f"[CARD_REWARD_DEBUG] Cards obtained so far: {card_count_before}"
            )

            # Optimized path may fall back to SimpleAgent which doesn't record
            # We need to ensure recording happens regardless of path taken
            # But avoid duplicate recording by checking if count increased

            # Check if optimized path already recorded by checking if counts changed
            # Optimized path records in _choose_card_reward_optimized() before returning
            # So we check if cards_obtained or cards_skipped increased

            if isinstance(action, CardRewardAction):
                # Try to match the card
                chosen_card_id = None
                for card in reward_cards:
                    if hasattr(card, "name") and card.name == action.name:
                        chosen_card_id = self._card_id_for_tracking(card)
                        logging.info(
                            f"[CARD_REWARD_DEBUG] MATCHED card: {chosen_card_id} with name {card.name}"
                        )
                        break

                if chosen_card_id:
                    # Check if this card is already the last recorded card (optimized path just recorded it)
                    was_already_recorded = False
                    if card_count_before > 0 and self.game_tracker.cards_obtained:
                        last_recorded = self.game_tracker.cards_obtained[-1]
                        if last_recorded == chosen_card_id:
                            was_already_recorded = True
                            logging.info(
                                f"[CARD_REWARD_DEBUG] Card '{chosen_card_id}' is already the last recorded - skipping duplicate"
                            )

                    if not was_already_recorded:
                        logging.info(
                            f"[CARD_REWARD_DEBUG] Recording card choice: {chosen_card_id}"
                        )
                        self.game_tracker.record_card_choice(
                            chosen=chosen_card_id,
                            skipped=len(reward_cards) - 1,
                            available=self._card_ids_for_tracking(reward_cards),
                        )

                        card_count_after = (
                            len(self.game_tracker.cards_obtained)
                            if self.game_tracker.cards_obtained
                            else 0
                        )
                        if card_count_after > card_count_before:
                            logging.info(
                                f"[CARD_REWARD_DEBUG] ✓ Recording successful (count increased {card_count_before}→{card_count_after})"
                            )
                        else:
                            logging.info(
                                f"[CARD_REWARD_DEBUG] ⚠ Recording attempted but count didn't increase"
                            )

            elif isinstance(action, CancelAction):
                # For skips, check if cards_skipped just increased
                skipped_before = (
                    self.game_tracker.cards_skipped
                    if hasattr(self.game_tracker, "cards_skipped")
                    else 0
                )

                # Check if the last record was a skip for these exact same cards
                # We can't easily detect this, so we'll check if count is suspicious
                # For now, only record if the count seems reasonable (not just incremented)
                # Actually, simplest is to check if cards_skipped is at expected value
                # Expected would be: previous_skipped + len(reward_cards)

                logging.info(
                    f"[CARD_REWARD_DEBUG] Action is CancelAction - cards_skipped before: {skipped_before}"
                )

                # Only record if this doesn't look like a duplicate
                # We'll use a simple heuristic: only record if we're in the optimized path
                # that fell back to SimpleAgent (which doesn't record)
                # But we can't detect that reliably, so we'll just record for now

                self.game_tracker.record_card_choice(
                    chosen=None,
                    skipped=len(reward_cards),
                    available=self._card_ids_for_tracking(reward_cards),
                )

                skipped_after = (
                    self.game_tracker.cards_skipped
                    if hasattr(self.game_tracker, "cards_skipped")
                    else 0
                )
                logging.info(
                    f"[CARD_REWARD_DEBUG] Skip recorded (skipped: {skipped_before}→{skipped_after})"
                )
            else:
                logging.warning(
                    f"[CARD_REWARD_DEBUG] Unexpected action type: {type(action).__name__}"
                )
        else:
            logging.warning(
                f"[CARD_REWARD_DEBUG] Cannot record - game_tracker={self.game_tracker is not None}, reward_cards={len(reward_cards)}"
            )

        logging.info(f"[CARD_REWARD_DEBUG] choose_card_reward returning action\n")
        return action

    def _choose_card_reward_optimized(self):
        """
        Use synergy-based card selection.

        Returns:
            CardRewardAction or CancelAction
        """
        try:
            reward_cards = self.game.screen.cards

            if not reward_cards:
                return CancelAction()

            must_choose_card = self._is_generated_combat_card_choice(reward_cards)

            # Create decision context with error handling
            try:
                context = DecisionContext(self.game)
            except Exception as e:
                # If context creation fails, fall back to simple logic
                import sys

                print(f"Error creating DecisionContext: {e}", file=sys.stderr)
                return super().choose_card_reward()

            # Ironclad's deck strategy/evaluator supersedes the legacy copy caps;
            # some old zero-copy caps are intentional skips for SimpleAgent only.
            if (
                not must_choose_card
                and self.game.screen.can_skip
                and not self.game.in_combat
                and self.deck_strategy is None
            ):
                pickable_cards = [
                    card
                    for card in reward_cards
                    if self.priorities.needs_more_copies(
                        card, self.count_copies_in_deck(card), self.game.deck
                    )
                ]
            else:
                pickable_cards = reward_cards

            if not pickable_cards:
                if must_choose_card:
                    pickable_cards = reward_cards
                # Only use bowl when not in combat (bowl is for post-combat rewards only)
                elif self.game.screen.can_bowl and not self.game.in_combat:
                    return CardRewardAction(bowl=True)
                else:
                    self.skipped_cards = True
                    # Track skipped card choice
                    if self.game_tracker:
                        self.game_tracker.record_card_choice(
                            chosen=None,
                            skipped=len(reward_cards),
                            available=self._card_ids_for_tracking(reward_cards),
                        )
                        # 记录跳过决策
                        self.game_tracker.record_decision(
                            decision_type="reward",
                            confidence=0.5,  # 跳过卡牌的置信度较低
                            used_fallback=False,
                        )
                    return CancelAction()

            strategy_scores = {}
            if self.deck_strategy is not None and not must_choose_card:
                strategy_filtered = []
                for card in pickable_cards:
                    try:
                        should_pick, reason = self.deck_strategy.should_pick_card(
                            card, context
                        )
                    except Exception as exc:
                        logging.info(
                            "[REWARD] Deck strategy check failed for %s: %s",
                            getattr(card, "card_id", card),
                            exc,
                        )
                        should_pick = True
                        reason = "strategy unavailable"
                    logging.info(
                        "[REWARD] Deck strategy: %s -> %s (%s)",
                        getattr(card, "card_id", card),
                        "take" if should_pick else "skip",
                        reason,
                    )
                    if should_pick:
                        if hasattr(self.deck_strategy, "_get_card_baseline_score"):
                            try:
                                strategy_scores[id(card)] = float(
                                    self.deck_strategy._get_card_baseline_score(
                                        self._normalize_card_name(card)
                                    )
                                )
                            except Exception:
                                strategy_scores[id(card)] = None
                        strategy_filtered.append(card)

                if strategy_filtered:
                    pickable_cards = strategy_filtered
                elif self.game.screen.can_skip:
                    logging.info(
                        "[REWARD] Deck strategy rejected all cards - skipping reward"
                    )
                    self.skipped_cards = True
                    if self.game_tracker:
                        self.game_tracker.record_card_choice(
                            chosen=None,
                            skipped=len(reward_cards),
                            available=self._card_ids_for_tracking(reward_cards),
                        )
                    return CancelAction()

            # Limit Break conditional check (A20 expert strategy)
            # Only pick Limit Break when we have Strength support
            limit_break_card = next(
                (
                    c
                    for c in pickable_cards
                    if self._normalize_card_name(c) == "Limit Break"
                ),
                None,
            )
            if limit_break_card and not must_choose_card:
                current_strength = (
                    context.strength if hasattr(context, "strength") else 0
                )

                # Check if we have Strength scaling cards
                strength_scaling_cards = ["Demon Form", "Inflame", "Spot Weakness"]
                has_strength_scaling = (
                    any(
                        self._normalize_card_name(c) in strength_scaling_cards
                        for c in self.game.deck
                    )
                    if hasattr(self.game, "deck") and self.game.deck
                    else False
                )

                # Skip Limit Break if no Strength support
                if current_strength < 5 and not has_strength_scaling:
                    import sys

                    logging.info(
                        f"[REWARD] Skipping Limit Break - no Strength support (Str={current_strength}, has_scaling={has_strength_scaling})\n"
                    )
                    pickable_cards = [
                        c
                        for c in pickable_cards
                        if self._normalize_card_name(c) != "Limit Break"
                    ]

                    if not pickable_cards:
                        # No other cards worth taking
                        # Only use bowl when not in combat
                        if self.game.screen.can_bowl and not self.game.in_combat:
                            return CardRewardAction(bowl=True)
                        else:
                            return CancelAction()

            def _normalize_boss_name(value):
                return "".join(
                    ch for ch in str(value or "").lower() if ch.isalnum()
                )

            act_1_frontload_cards = set(
                getattr(self.card_evaluator, "ACT_1_FRONTLOAD_COVERAGE", set())
                or set()
            )
            act_1_frontload_cards.update(
                getattr(self.card_evaluator, "ACT_1_PREMIUM_FRONTLOAD", set())
                or set()
            )
            act_1_frontload_cards.update(
                {
                    "Bludgeon",
                    "Combust",
                    "Feed",
                    "Fiend Fire",
                    "Heavy Blade",
                    "Immolate",
                    "Perfected Strike",
                    "Reaper",
                    "Sever Soul",
                }
            )
            act_1_block_cards = set(
                getattr(self.card_evaluator, "ACT_1_SURVIVAL_BLOCK", set())
                or set()
            )
            act_1_block_cards.update(
                getattr(self.card_evaluator, "BLOCK_SUPPORT", set()) or set()
            )
            act_1_block_cards.update({"Metallicize"})

            deck_ids = [
                self._normalize_card_name(deck_card)
                for deck_card in (getattr(self.game, "deck", None) or [])
            ]
            frontload_count = sum(
                1 for card_id in deck_ids if card_id in act_1_frontload_cards
            )
            act_boss = _normalize_boss_name(getattr(self.game, "act_boss", None))
            slime_boss_frontload_gap = (
                getattr(context, "act", 0) == 1
                and "slimeboss" in act_boss
                and frontload_count < 4
                and (getattr(context, "floor", 0) or 0) <= 15
            )
            if slime_boss_frontload_gap:
                logging.info(
                    "[REWARD] Slime Boss frontload gap: frontload=%s deck_size=%s",
                    frontload_count,
                    len(deck_ids),
                )

            act_1_strength_enablers = {
                "Demon Form",
                "Inflame",
                "Spot Weakness",
            }
            act_1_premium_frontload = {
                "Bludgeon",
                "Carnage",
                "Fiend Fire",
                "Immolate",
            }
            act_1_efficient_frontload = {
                "Anger",
                "Carnage",
                "Combust",
                "Cleave",
                "Clothesline",
                "Fiend Fire",
                "Hemokinesis",
                "Immolate",
                "Iron Wave",
                "Pommel Strike",
                "Sever Soul",
                "Twin Strike",
                "Uppercut",
                "Whirlwind",
            }
            act_1_havoc_support = {
                "Corruption",
                "Dark Embrace",
                "Feel No Pain",
                "Fiend Fire",
                "Second Wind",
                "Sever Soul",
            }
            act_1_power_through_support = {
                "Burning Pact",
                "Corruption",
                "Dark Embrace",
                "Evolve",
                "Feel No Pain",
                "Second Wind",
                "True Grit",
            }
            act_1_foundation_cards = (
                act_1_efficient_frontload
                | act_1_strength_enablers
                | act_1_block_cards
                | {"Armaments", "Battle Trance", "Offering", "Shockwave"}
            )
            has_strength_support = any(
                card_id in act_1_strength_enablers for card_id in deck_ids
            )
            has_havoc_support = any(
                card_id in act_1_havoc_support for card_id in deck_ids
            )
            has_power_through_support = any(
                card_id in act_1_power_through_support for card_id in deck_ids
            )
            feed_count = sum(1 for card_id in deck_ids if card_id == "Feed")
            anger_count = sum(1 for card_id in deck_ids if card_id == "Anger")
            havoc_count = sum(1 for card_id in deck_ids if card_id == "Havoc")
            disarm_count = sum(1 for card_id in deck_ids if card_id == "Disarm")
            has_heavy_blade_in_deck = "Heavy Blade" in deck_ids
            has_heavy_blade = "Heavy Blade" in deck_ids or any(
                self._normalize_card_name(card) == "Heavy Blade"
                for card in pickable_cards
            )
            has_better_unsupported_heavy_blade_option = any(
                self._normalize_card_name(card)
                in (act_1_efficient_frontload | act_1_strength_enablers)
                for card in pickable_cards
            )
            has_better_unsupported_havoc_option = any(
                self._normalize_card_name(card) in act_1_foundation_cards
                for card in pickable_cards
            )
            act_1_rage_better_options = (
                act_1_frontload_cards
                | act_1_block_cards
                | {"Armaments", "Battle Trance", "Offering", "Shockwave"}
            )
            has_better_early_rage_option = any(
                self._normalize_card_name(card) in act_1_rage_better_options
                for card in pickable_cards
            )
            has_better_slime_frontload_option = any(
                self._normalize_card_name(card) in act_1_frontload_cards
                for card in pickable_cards
            )
            duplicate_anger_upgrade_options = (
                {"Inflame", "Spot Weakness", "Feed"}
                | act_1_block_cards
                | {"Armaments", "Battle Trance", "Offering", "Shockwave"}
            )
            has_better_duplicate_anger_option = any(
                self._normalize_card_name(card) in duplicate_anger_upgrade_options
                for card in pickable_cards
            )
            current_hp = self._safe_float(getattr(self.game, "current_hp", 0), 0.0)
            max_hp = max(self._safe_float(getattr(self.game, "max_hp", 1), 1.0), 1.0)
            player_hp_pct = current_hp / max_hp
            has_act_1_boss_damage_plan = frontload_count >= 3 or any(
                card_id
                in {
                    "Blood for Blood",
                    "Heavy Blade",
                    "Shockwave",
                    "Thunderclap",
                }
                for card_id in deck_ids
            )
            power_through_survival_gap = (
                getattr(context, "act", 0) == 1
                and (getattr(context, "floor", 0) or 0) <= 15
                and (has_power_through_support or has_act_1_boss_damage_plan)
                and (player_hp_pct <= 0.75 or has_power_through_support)
            )
            slow_slime_boss_utility_cards = {
                "Burning Pact",
                "Second Wind",
                "Forethought",
            }

            def reward_selection_score(card):
                strategy_score = strategy_scores.get(id(card))
                evaluator_score = None
                if self.card_evaluator:
                    try:
                        evaluator_score = self.card_evaluator.evaluate_card(card, context)
                    except Exception:
                        evaluator_score = None

                if strategy_score is not None:
                    if strategy_score >= 65 and evaluator_score is not None:
                        score = max(strategy_score, evaluator_score)
                    elif evaluator_score is not None:
                        if getattr(context, "act", 0) == 1 and evaluator_score >= 75:
                            score = max(strategy_score, evaluator_score)
                        else:
                            score = min(strategy_score, evaluator_score)
                    else:
                        score = strategy_score
                elif evaluator_score is not None:
                    score = evaluator_score
                else:
                    score = 50

                card_name = self._normalize_card_name(card)
                if (
                    card_name == "Disarm"
                    and self._safe_int(getattr(context, "act", 0), 0) == 2
                    and disarm_count == 0
                ):
                    score = max(score, 108 if "champ" in act_boss else 96)

                if (
                    getattr(context, "act", 0) == 1
                    and (getattr(context, "floor", 0) or 0) <= 15
                ):
                    if card_name in act_1_strength_enablers and has_heavy_blade_in_deck:
                        score = max(score, 90)
                    if card_name in act_1_premium_frontload:
                        score = max(score, 108 if card_name == "Immolate" else 92)
                    if (
                        card_name == "Twin Strike"
                        and (getattr(context, "floor", 0) or 0) <= 8
                        and frontload_count < 3
                    ):
                        score = max(score, 78)
                    if card_name == "Power Through" and power_through_survival_gap:
                        score = max(score, 104)
                    if card_name == "Feed" and feed_count == 0:
                        score = max(score, 100)
                    if (
                        card_name in act_1_efficient_frontload
                        and has_heavy_blade_in_deck
                        and not has_strength_support
                    ):
                        score = max(score, 86)
                    if card_name == "Havoc" and havoc_count > 0:
                        score = min(score, 60)
                    if (
                        card_name == "Anger"
                        and anger_count > 0
                        and has_better_duplicate_anger_option
                    ):
                        score = min(score, 60)
                    if (
                        card_name == "Havoc"
                        and not has_havoc_support
                        and has_better_unsupported_havoc_option
                    ):
                        score = min(score, 48)
                    if (
                        card_name == "Heavy Blade"
                        and not has_strength_support
                        and has_better_unsupported_heavy_blade_option
                    ):
                        score = min(score, 72)
                    if card_name == "Rage" and has_better_early_rage_option:
                        score = min(score, 60)

                if slime_boss_frontload_gap:
                    if (
                        card_name in act_1_strength_enablers
                        and has_heavy_blade
                    ):
                        return max(score, 94)
                    if (
                        card_name == "Heavy Blade"
                        and not has_strength_support
                        and has_better_unsupported_heavy_blade_option
                    ):
                        return min(score, 72)
                    if card_name in act_1_frontload_cards:
                        return max(score, 94)
                    if card_name == "Power Through" and power_through_survival_gap:
                        return max(score, 104)
                    if (
                        card_name in slow_slime_boss_utility_cards
                        and has_better_slime_frontload_option
                    ):
                        return min(score, 64)
                    if card_name in act_1_block_cards:
                        return min(score, 68)
                return score

            def reward_tiebreaker_score(card):
                if self.card_evaluator:
                    try:
                        return self.card_evaluator.evaluate_card(card, context)
                    except Exception:
                        pass
                return reward_selection_score(card)

            # Deck size limit check (keep deck lean)
            deck_size = (
                len(self.game.deck)
                if hasattr(self.game, "deck") and self.game.deck
                else 10
            )
            if deck_size >= 18 and not must_choose_card:
                import sys

                # Be very selective - only high priority cards
                # Get scores for all pickable cards
                scored_cards = []
                for card in pickable_cards:
                    scored_cards.append((card, reward_selection_score(card)))

                # Filter for high priority cards (score >= 65, reduced from 75 to reduce skipping)
                high_priority_cards = [
                    (card, card_score)
                    for card, card_score in scored_cards
                    if card_score >= 65
                ]

                if high_priority_cards:
                    logging.info(
                        f"[REWARD] Deck size {deck_size}, being selective (score >= 65)\n"
                    )
                    pickable_cards = [card for card, _ in high_priority_cards]
                else:
                    # No good cards - skip to keep deck lean
                    logging.info(
                        f"[REWARD] Deck too large ({deck_size}) and no good cards (score >= 65) - skipping\n"
                    )
                    # Only use bowl when not in combat
                    if self.game.screen.can_bowl and not self.game.in_combat:
                        return CardRewardAction(bowl=True)
                    else:
                        self.skipped_cards = True
                        if self.game_tracker:
                            self.game_tracker.record_card_choice(
                                chosen=None,
                                skipped=len(reward_cards),
                                available=self._card_ids_for_tracking(reward_cards),
                            )
                        return CancelAction()

            # Use synergy evaluator to rank cards
            try:
                if strategy_scores:
                    best_card = max(
                        pickable_cards,
                        key=lambda card: (
                            reward_selection_score(card),
                            reward_tiebreaker_score(card),
                        ),
                    )
                else:
                    best_card = self.card_evaluator.get_best_card(pickable_cards, context)
            except Exception as e:
                import sys

                print(f"Error in card evaluator: {e}", file=sys.stderr)
                # Fall back to simple logic
                return super().choose_card_reward()

            if best_card:
                # Track card choice
                if self.game_tracker:
                    self.game_tracker.record_card_choice(
                        chosen=self._card_id_for_tracking(best_card),
                        skipped=len(reward_cards) - 1,
                        available=self._card_ids_for_tracking(reward_cards),
                    )

                # Record decision
                self.decision_history.append(
                    {
                        "type": "card_reward",
                        "card": self._card_id_for_tracking(best_card),
                        "floor": context.floor,
                        "archetype": context.deck_archetype,
                    }
                )

                # Record to game_tracker
                if self.game_tracker:
                    self.game_tracker.record_decision(
                        decision_type="reward",
                        confidence=0.8,  # 卡牌选择默认置信度
                        used_fallback=False,
                    )

                return CardRewardAction(best_card)
            else:
                if must_choose_card and reward_cards:
                    logging.info(
                        "[REWARD] Generated combat card choice had no evaluator pick; choosing first option"
                    )
                    return CardRewardAction(reward_cards[0])
                return CancelAction()
        except Exception as e:
            import sys

            print(f"Error in _choose_card_reward_optimized: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            # Fall back to parent's logic
            return super().choose_card_reward()

    def use_next_potion(self):
        """
        Enhanced potion usage logic.

        Uses potions not just in boss fights but also in:
        - Elite fights when dangerous
        - High-damage situations
        - When potion provides high value
        - Based on potion type and current needs

        Returns:
            PotionAction or None
        """
        potions = self.game.get_real_potions()

        if not potions:
            return None

        # Calculate current needs
        current_hp = self._safe_float(getattr(self.game, "current_hp", 0), 0.0)
        max_hp = max(self._safe_float(getattr(self.game, "max_hp", 1), 1.0), 1.0)
        hp_pct = current_hp / max_hp
        incoming_damage = self.get_incoming_damage()
        alive_monsters = [
            m for m in self.game.monsters if self._is_live_monster(m)
        ]
        is_elite = "Elite" in self.game.room_type
        is_boss = "Boss" in self.game.room_type

        # Evaluate combat danger
        danger_level = self._evaluate_combat_danger(None)

        # Filter and prioritize potions based on situation
        potions_to_use = []

        for potion in potions:
            if hasattr(potion, "can_use") and not potion.can_use:
                continue
            if potion_is_exhaust_hand_select(potion):
                continue
            potion_name = str(getattr(potion, "name", None) or potion_id(potion) or "")
            potion_name_lower = potion_name.lower()

            # Prioritize potions based on situation
            use_potion = False

            # Healing potions - use when HP is low and in danger
            if (
                "heal" in potion_name_lower
                or "health" in potion_name_lower
                or "strawberry" in potion_name_lower
                or "apple" in potion_name_lower
                or getattr(potion, "effect_type", None) in (
                    "heal",
                    "heal_percent",
                    "regen",
                    "fairy",
                    "max_hp",
                )
            ):
                # Use healing potions when HP is critical or in dangerous situations
                if (
                    hp_pct < 0.3 or (hp_pct < 0.5 and danger_level > 0.5)
                ) and incoming_damage > 0:
                    use_potion = True
                    potions_to_use.append((3, potion))

            # Damage potions - use when multiple monsters or dangerous enemies
            elif (
                "damage" in potion_name_lower
                or "strength" in potion_name_lower
                or "fire" in potion_name_lower
                or "ice" in potion_name_lower
                or "lightning" in potion_name_lower
                or getattr(potion, "effect_type", None) in ("damage", "poison")
            ):
                # Use damage potions in elite/boss fights or when multiple monsters
                if (
                    is_elite or is_boss or len(alive_monsters) >= 2
                ) and danger_level > 0.4:
                    use_potion = True
                    potions_to_use.append((2, potion))

            # Defensive potions - use when incoming damage is high
            elif (
                "block" in potion_name_lower
                or "shield" in potion_name_lower
                or "barrier" in potion_name_lower
                or getattr(potion, "effect_type", None) in (
                    "block",
                    "plated_armor",
                    "metallicize",
                )
            ):
                # Use defensive potions when incoming damage exceeds current HP or block
                current_block = self._safe_float(
                    getattr(getattr(self.game, "player", None), "block", 0),
                    0.0,
                )
                if incoming_damage > current_block + current_hp * 0.5:
                    use_potion = True
                    potions_to_use.append((1, potion))

            # Other potions - use based on general danger
            else:
                if danger_level > 0.7:
                    use_potion = True
                    potions_to_use.append((0, potion))

        # Sort potions by priority (highest first)
        potions_to_use.sort(reverse=True, key=lambda x: x[0])

        # Use the highest priority potion
        if potions_to_use:
            _, potion = potions_to_use[0]
            potion_name = str(getattr(potion, "name", None) or potion_id(potion) or "")
            potion_name_lower = potion_name.lower()
            if getattr(potion, "requires_target", False):
                # For damage potions, target highest HP monster; for others, target as appropriate
                if (
                    "damage" in potion_name_lower
                    or getattr(potion, "effect_type", None) in ("damage", "poison")
                ):
                    target = max(alive_monsters, key=lambda m: self._monster_current_hp(m))
                elif str(getattr(potion, "effect_type", "")).startswith("debuff_"):
                    target = max(alive_monsters, key=lambda m: self._monster_current_hp(m))
                else:
                    target = self.get_low_hp_target()
                potion_action = PotionAction(True, potion=potion, target_monster=target)
            else:
                potion_action = PotionAction(True, potion=potion)

            if self.game_tracker:
                self.game_tracker.record_potion_use()

            return potion_action

        # Fallback: always use potions in boss fights if nothing else
        if is_boss:
            potion_action = super().use_next_potion()
            if potion_action and self.game_tracker:
                self.game_tracker.record_potion_use()
            return potion_action

        return None

    def _evaluate_combat_danger(self, context):
        """
        Evaluate how dangerous the current combat is (0-1).

        Considers:
        - Number of monsters
        - Incoming damage
        - Player HP percentage

        Args:
            context: DecisionContext (or None)

        Returns:
            Danger level 0-1
        """
        danger = 0.0

        # Monster count
        alive_monsters = [
            m for m in self.game.monsters if self._is_live_monster(m)
        ]
        danger += min(len(alive_monsters) * 0.15, 0.4)

        current_hp = self._safe_float(getattr(self.game, "current_hp", 0), 0.0)
        max_hp = max(self._safe_float(getattr(self.game, "max_hp", 1), 1.0), 1.0)

        # Incoming damage
        incoming = self.get_incoming_damage()
        danger += min(incoming / max_hp, 0.4)

        # HP percentage
        hp_pct = current_hp / max_hp
        if hp_pct < 0.3:
            danger += 0.3

        # Elite or boss
        if "Elite" in self.game.room_type or "Boss" in self.game.room_type:
            danger += 0.2

        return min(danger, 1.0)

    def get_deck_stats(self):
        """
        Get statistics about current deck.

        Returns:
            Dictionary with deck metrics (if optimized components available)
        """
        if self.deck_analyzer and OPTIMIZED_AI_AVAILABLE:
            try:
                context = DecisionContext(self.game)
                return self.deck_analyzer.get_deck_stats(context)
            except Exception as e:
                return {"error": str(e)}
        else:
            return {"error": "Deck analyzer not available"}

    def get_decision_summary(self):
        """
        Get summary of decisions made this game.

        Returns:
            Dictionary with decision statistics
        """
        if not self.decision_history:
            return {"total_decisions": 0}

        summary = {
            "total_decisions": len(self.decision_history),
            "combat_decisions": sum(
                1 for d in self.decision_history if d.get("type") == "combat"
            ),
            "card_rewards": sum(
                1 for d in self.decision_history if d.get("type") == "card_reward"
            ),
            "avg_confidence": 0,
        }

        # Calculate average confidence for combat decisions
        combat_confidences = [
            d.get("confidence", 0)
            for d in self.decision_history
            if d.get("type") == "combat"
        ]
        if combat_confidences:
            summary["avg_confidence"] = sum(combat_confidences) / len(
                combat_confidences
            )

        return summary
