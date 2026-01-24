"""
Reward calculator for shaping rewards in RL training.

Provides dense reward signals for combat survival, damage dealt, game progression, etc.
"""

import math
from typing import Optional, Iterable
from spirecomm.spire.game import Game
from spirecomm.spire.screen import ScreenType
from spirecomm.spire.card import CardRarity
from spirecomm.ai.decision.base import DecisionContext
from spirecomm.ai.heuristics.card import SynergyCardEvaluator


class RewardCalculator:
    """
    Calculates shaped rewards for RL agent training.

    Reward components:
    - Combat rewards: damage dealt, kills, HP loss
    - Progression rewards: floors, elites, bosses
    - Acquisition rewards: cards, relics, gold
    - Terminal rewards: victory (+1000), defeat (-500)
    """

    # Combat reward weights
    DAMAGE_REWARD_SCALE = 0.05
    DAMAGE_REWARD_CAP = 5.0
    KILL_REWARD = 5.0
    ALL_LETHAL_BONUS = 15.0
    HP_LOSS_PENALTY = 50.0  # Applied to HP loss ratio (lost / max)
    TURN_END_PENALTY = -0.05

    # Progression reward weights
    FLOOR_REWARD_SCALE = 3.0
    ELITE_REWARD = 20.0
    BOSS_REWARD = 60.0

    # Acquisition reward weights
    CARD_REWARD_BASE = 2.0
    CARD_SCORE_NORMALIZER = 100.0
    CARD_SCORE_MAX_MULT = 2.0
    CARD_SKIP_REWARD = 0.02
    CARD_SKIP_PENALTY = 0.02
    CARD_DECK_SIZE_THRESHOLD = 20
    CARD_DECK_SIZE_PENALTY = 0.01
    RELIC_REWARD = 10.0
    GOLD_REWARD_SCALE = 0.005

    # Terminal rewards
    VICTORY_REWARD = 1000.0
    DEFEAT_PENALTY = -500.0

    def __init__(self):
        """Initialize reward calculator with tracking."""
        self.card_evaluator: Optional[SynergyCardEvaluator] = None
        self.card_evaluator_class: Optional[str] = None
        self.reset()

    @staticmethod
    def _safe_attr(obj, *attrs, default=None):
        """Safely get nested attribute with fallback to default."""
        result = obj
        for attr in attrs:
            if hasattr(result, attr):
                result = getattr(result, attr)
                if result is None:
                    return default
            else:
                return default
        return result if result is not None else default

    def reset(self) -> None:
        """Reset tracking for new episode."""
        self.total_damage_dealt = 0
        self.total_damage_taken = 0
        self.monsters_killed = 0
        self.last_floor = 0
        self.cards_obtained = 0
        self.relics_obtained = 0
        self.gold_obtained = 0
        self.elites_killed = 0
        self.bosses_killed = 0

        # Track previous state for delta calculation
        self.last_player_hp = None
        self.last_monsters_hp = {}  # monster_index -> current_hp

    def calculate_combat_reward(self, game: Game, damage_dealt: int = 0,
                                monster_killed: bool = False,
                                all_monsters_killed: bool = False,
                                hp_lost: int = 0, turn_ended: bool = False) -> float:
        """Calculate reward for combat actions."""
        reward = 0.0
        reward += min(damage_dealt * self.DAMAGE_REWARD_SCALE, self.DAMAGE_REWARD_CAP)
        self.total_damage_dealt += damage_dealt
        if monster_killed:
            reward += self.KILL_REWARD
            self.monsters_killed += 1
        if all_monsters_killed:
            reward += self.ALL_LETHAL_BONUS
        if hp_lost > 0:
            max_hp = self._safe_attr(game, 'player', 'max_hp') or self._safe_attr(game, 'max_hp')
            if max_hp:
                hp_loss_ratio = hp_lost / max(max_hp, 1)
                reward -= self.HP_LOSS_PENALTY * hp_loss_ratio
            self.total_damage_taken += hp_lost
        if turn_ended:
            reward += self.TURN_END_PENALTY
        return reward

    def calculate_progression_reward(self, game: Game, floor_advanced: bool = False,
                                    elite_killed: bool = False,
                                    boss_killed: bool = False) -> float:
        """Calculate reward for game progression."""
        reward = 0.0
        if floor_advanced:
            floors_gained = game.floor - self.last_floor
            reward += floors_gained * self.FLOOR_REWARD_SCALE
            self.last_floor = game.floor
        if elite_killed:
            reward += self.ELITE_REWARD
            self.elites_killed += 1
        if boss_killed:
            reward += self.BOSS_REWARD
            self.bosses_killed += 1
        return reward

    def calculate_acquisition_reward(self, game: Game, card_obtained: bool = False,
                                     card_power_score: float = 1.0,
                                     relic_obtained: bool = False,
                                     gold_obtained: int = 0) -> float:
        """Calculate reward for acquiring cards, relics, gold."""
        reward = 0.0
        if card_obtained:
            reward += self.CARD_REWARD_BASE * card_power_score
            self.cards_obtained += 1
        if relic_obtained:
            reward += self.RELIC_REWARD
            self.relics_obtained += 1
        if gold_obtained > 0:
            reward += self.GOLD_REWARD_SCALE * gold_obtained
            self.gold_obtained += gold_obtained
        return reward

    def calculate_terminal_reward(self, victory: bool) -> float:
        """Calculate terminal reward for episode end."""
        return self.VICTORY_REWARD if victory else self.DEFEAT_PENALTY

    def calculate_step_reward(self, current_game: Game, last_game: Game, action_type: str = "combat") -> float:
        """
        Calculate reward for a single step by comparing game states.

        Auto-detects:
        - Damage dealt (monster HP decrease)
        - Monsters killed (monster died or disappeared)
        - HP lost (player HP decrease)
        - All monsters killed (combat end)
        - Floor advancement (game progression)
        - Card acquisition (deck size increase)
        - Relic acquisition (relic list growth)
        - Gold acquisition (gold increase)
        - Game over / victory (terminal rewards)

        Args:
            current_game: Current game state
            last_game: Previous game state (before action)
            action_type: Type of action ("combat", "progression", etc.)

        Returns:
            Calculated reward for this step
        """
        reward = 0.0

        # === TERMINAL REWARDS (highest priority) ===
        # Check for game over first
        if "GAME_OVER" in str(current_game.screen_type):
            # Determine victory vs defeat
            victory = self._is_victory(current_game)
            reward += self.calculate_terminal_reward(victory)
            return reward  # Terminal reward is final, no other rewards

        # === COMBAT REWARDS (dense) ===
        if current_game.in_combat and last_game.in_combat:
            # Track damage dealt to monsters
            damage_dealt = 0
            monster_killed = False
            all_monsters_killed = False

            # Get current monsters
            current_monsters = current_game.monsters if current_game.monsters else []
            last_monsters = last_game.monsters if last_game.monsters else []

            # Build mapping of monster_index -> HP for comparison
            current_monster_hp = {}
            for monster in current_monsters:
                if hasattr(monster, 'monster_index') and hasattr(monster, 'current_hp'):
                    current_monster_hp[monster.monster_index] = monster.current_hp

            # Compare with last state to detect damage and kills
            for last_monster in last_monsters:
                if not hasattr(last_monster, 'monster_index'):
                    continue

                idx = last_monster.monster_index
                last_hp = last_monster.current_hp if hasattr(last_monster, 'current_hp') else 0

                # Check if monster still exists
                if idx in current_monster_hp:
                    current_hp = current_monster_hp[idx]

                    # Monster took damage
                    if current_hp < last_hp:
                        damage_dealt += (last_hp - current_hp)

                    # Monster died
                    if current_hp <= 0 and last_hp > 0:
                        monster_killed = True
                else:
                    # Monster disappeared (died or removed)
                    if last_hp > 0:
                        monster_killed = True

            # Check if all monsters are now dead
            if len(current_monsters) > 0:
                all_alive = any(m.current_hp > 0 for m in current_monsters if hasattr(m, 'current_hp'))
                all_monsters_killed = not all_alive

            # Track HP lost
            hp_lost = 0
            current_hp = self._safe_attr(current_game, 'player', 'current_hp', default=0)
            last_hp = self._safe_attr(last_game, 'player', 'current_hp', default=0)

            if current_hp < last_hp:
                hp_lost = (last_hp - current_hp)

            # Detect turn end (turn number increased)
            turn_ended = False
            if (hasattr(current_game, 'turn') and hasattr(last_game, 'turn') and
                current_game.turn > last_game.turn):
                turn_ended = True

            # Calculate combat reward
            reward += self.calculate_combat_reward(
                current_game,
                damage_dealt=damage_dealt,
                monster_killed=monster_killed,
                all_monsters_killed=all_monsters_killed,
                hp_lost=hp_lost,
                turn_ended=turn_ended
            )
        elif last_game.in_combat and not current_game.in_combat:
            combat_won = self._is_combat_victory(current_game)
            had_alive_monsters = self._had_alive_monsters(last_game.monsters if last_game.monsters else [])
            reward += self.calculate_combat_reward(
                last_game,
                damage_dealt=0,
                monster_killed=combat_won and had_alive_monsters,
                all_monsters_killed=combat_won,
                hp_lost=0,
                turn_ended=False
            )
            if combat_won:
                elite_killed = self._is_elite_room(last_game)
                boss_killed = self._is_boss_room(last_game)
                if elite_killed or boss_killed:
                    reward += self.calculate_progression_reward(
                        current_game,
                        floor_advanced=False,
                        elite_killed=elite_killed,
                        boss_killed=boss_killed
                    )

        # === PROGRESSION REWARDS ===
        # Floor advancement
        if hasattr(current_game, 'floor') and hasattr(last_game, 'floor'):
            floor_advanced = current_game.floor > last_game.floor
            if floor_advanced:
                reward += self.calculate_progression_reward(
                    current_game,
                    floor_advanced=True,
                    elite_killed=False,  # TODO: detect elite kills
                    boss_killed=False    # TODO: detect boss kills
                )

        # === ACQUISITION REWARDS ===
        # Card acquisition
        current_deck_size = len(current_game.deck) if current_game.deck else 0
        last_deck_size = len(last_game.deck) if last_game.deck else 0
        if current_deck_size > last_deck_size:
            reward += self._calculate_card_reward(current_game, last_game)
        if last_game.screen_type == ScreenType.CARD_REWARD and current_game.screen_type != ScreenType.CARD_REWARD:
            reward += self._calculate_card_choice_reward(current_game, last_game)

        # Relic acquisition
        current_relics = len(current_game.relics) if current_game.relics else 0
        last_relics = len(last_game.relics) if last_game.relics else 0
        if current_relics > last_relics:
            # Agent obtained a relic
            reward += self.calculate_acquisition_reward(
                current_game,
                card_obtained=False,
                relic_obtained=True
            )

        # Gold acquisition (small reward)
        if hasattr(current_game, 'gold') and hasattr(last_game, 'gold'):
            gold_gained = current_game.gold - last_game.gold
            if gold_gained > 0:
                reward += self.calculate_acquisition_reward(
                    current_game,
                    gold_obtained=gold_gained
                )

        return reward

    def _is_victory(self, game: Game) -> bool:
        """
        Determine if game over was a victory or defeat.

        Victory indicators:
        - Screen type shows VICTORY
        - Player reached floor 55+ (final floor)
        - Heart defeated (special check)

        Args:
            game: Current game state at GAME_OVER screen

        Returns:
            True if victory, False if defeat
        """
        # Check screen type for victory indicators
        screen_str = str(game.screen_type).upper()
        if "VICTORY" in screen_str or "WIN" in screen_str:
            return True

        # Check if reached high floor (defeated final boss)
        if hasattr(game, 'floor') and game.floor >= 55:
            return True

        # Check if player is still alive at game over
        # (if game over but player HP > 0, likely won)
        if self._safe_attr(game, 'player', 'current_hp', default=0) > 0:
            return True

        # Default: assume defeat
        return False

    def _is_combat_victory(self, game: Game) -> bool:
        screen_type = getattr(game, 'screen_type', None)
        return screen_type in (ScreenType.COMBAT_REWARD, ScreenType.BOSS_REWARD)

    def _is_elite_room(self, game: Game) -> bool:
        room_type = str(getattr(game, 'room_type', '')).lower()
        return "elite" in room_type

    def _is_boss_room(self, game: Game) -> bool:
        room_type = str(getattr(game, 'room_type', '')).lower()
        return "boss" in room_type

    def _had_alive_monsters(self, monsters: Iterable) -> bool:
        for monster in monsters:
            if hasattr(monster, 'current_hp') and monster.current_hp > 0:
                return True
        return False

    def _get_card_evaluator(self, game: Game) -> SynergyCardEvaluator:
        player_class = getattr(getattr(game, 'character', None), 'name', None)
        if self.card_evaluator is None or self.card_evaluator_class != player_class:
            self.card_evaluator = SynergyCardEvaluator(player_class=player_class)
            self.card_evaluator_class = player_class
        return self.card_evaluator

    def _calculate_card_reward(self, current_game: Game, last_game: Game) -> float:
        if not current_game.deck:
            return 0.0
        last_uuids = {card.uuid for card in last_game.deck} if last_game.deck else set()
        new_cards = [card for card in current_game.deck if card.uuid not in last_uuids]
        if not new_cards:
            return 0.0
        try:
            context = DecisionContext(current_game)
            evaluator = self._get_card_evaluator(current_game)
        except Exception:
            return 0.0

        reward = 0.0
        for card in new_cards:
            try:
                score = evaluator.evaluate_card(card, context)
                normalized = max(0.0, min(score / self.CARD_SCORE_NORMALIZER, self.CARD_SCORE_MAX_MULT))
                reward += self.calculate_acquisition_reward(
                    current_game,
                    card_obtained=True,
                    card_power_score=normalized,
                    relic_obtained=False
                )
            except Exception:
                continue
        return reward

    def _calculate_card_choice_reward(self, current_game: Game, last_game: Game) -> float:
        screen = getattr(last_game, 'screen', None)
        candidates = getattr(screen, 'cards', None) if screen else None
        if not candidates:
            return 0.0

        last_uuids = {card.uuid for card in last_game.deck} if last_game.deck else set()
        new_cards = [card for card in current_game.deck if card.uuid not in last_uuids] if current_game.deck else []
        chosen_card = new_cards[0] if new_cards else None

        reward = 0.0
        has_uncommon_or_rare = any(
            getattr(card, 'rarity', None) in (CardRarity.UNCOMMON, CardRarity.RARE)
            for card in candidates
        )
        if chosen_card is None:
            if not has_uncommon_or_rare:
                reward += self.CARD_SKIP_REWARD
            else:
                reward -= self.CARD_SKIP_PENALTY
            return reward

        deck_size = len(current_game.deck) if current_game.deck else 0
        if (
            deck_size > self.CARD_DECK_SIZE_THRESHOLD
            and getattr(chosen_card, 'rarity', None) in (CardRarity.BASIC, CardRarity.COMMON)
        ):
            reward -= self.CARD_DECK_SIZE_PENALTY

        return reward


def calculate_step_reward(game: Game, action_type: str = "combat", **kwargs) -> float:
    """Convenience function to calculate reward for a single step."""
    calculator = RewardCalculator()
    if action_type == "combat":
        return calculator.calculate_combat_reward(game, **kwargs)
    elif action_type == "progression":
        return calculator.calculate_progression_reward(game, **kwargs)
    elif action_type == "acquisition":
        return calculator.calculate_acquisition_reward(game, **kwargs)
    elif action_type == "terminal":
        return calculator.calculate_terminal_reward(**kwargs)
    return 0.0
