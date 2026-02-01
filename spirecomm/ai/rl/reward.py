"""
Reward calculator for shaping rewards in RL training.

Provides dense reward signals for combat survival, damage dealt, game progression, etc.
"""

import logging
import math
import os
from typing import Optional, Iterable, Dict, Tuple
from spirecomm.spire.game import Game
from spirecomm.spire.screen import ScreenType
from spirecomm.spire.card import CardRarity
from spirecomm.spire.character import PlayerClass
from spirecomm.ai.priorities import (
    Priority,
    IroncladPriority,
    SilentPriority,
    DefectPowerPriority,
)

logger = logging.getLogger(__name__)


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
    DAMAGE_REWARD_SCALE = 0.07
    DAMAGE_REWARD_CAP = 5.0
    KILL_REWARD = 5.0
    ALL_LETHAL_BONUS = 15.0
    HP_LOSS_PENALTY = 35.0  # Applied to HP loss ratio (lost / max)
    TURN_END_PENALTY = -0.05
    ENEMY_STRENGTH_GAIN_PENALTY = 0.5
    ENEMY_STRENGTH_GAIN_CAP = 3.0

    # Progression reward weights
    FLOOR_REWARD_SCALE = 3.0
    ELITE_REWARD = 20.0
    BOSS_REWARD = 60.0
    BOSS_REWARD_MULT = 1.2

    # Acquisition reward weights
    CARD_REWARD_BASE = 2.0  # Still used - base reward for getting any card
    # Heuristic card scoring constants based on CARD_PRIORITY_LIST ordering.
    CARD_CHOICE_RELATIVE_SCALE = 0.2
    RELIC_REWARD = 10.0
    GOLD_REWARD_SCALE = 0.005

    # Terminal rewards
    VICTORY_REWARD = 300.0
    DEFEAT_PENALTY = -250.0

    def __init__(self):
        """Initialize reward calculator with tracking."""
        self._card_reward_debug = self._is_truthy(os.getenv("RL_CARD_REWARD_DEBUG", "1"))
        self._priority_by_class = {
            PlayerClass.IRONCLAD: IroncladPriority(),
            PlayerClass.THE_SILENT: SilentPriority(),
            PlayerClass.DEFECT: DefectPowerPriority(),
        }
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

    @staticmethod
    def _is_truthy(value: str) -> bool:
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

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
            reward += self.BOSS_REWARD * self.BOSS_REWARD_MULT
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

    def calculate_step_reward(
        self,
        current_game: Game,
        last_game: Game,
        action_type: str = "combat",
        debug_info: Optional[Dict] = None,
        action_context: Optional[Dict] = None,
    ) -> float:
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
        info = debug_info
        if info is not None:
            info.clear()
            info.update(
                {
                    "terminal_reward": 0.0,
                    "combat_reward": 0.0,
                    "progress_reward": 0.0,
                    "acquisition_reward": 0.0,
                    "card_choice_reward": 0.0,
                    "damage_dealt": 0,
                    "total_monster_hp_delta": 0,
                    "monster_count_last": 0,
                    "monster_count_current": 0,
                    "hp_lost": 0,
                    "energy_spent": 0,
                    "block_delta": 0,
                    "turn_ended": False,
                    "monster_killed": False,
                    "all_monsters_killed": False,
                    "floor_advanced": False,
                    "elite_killed": False,
                    "boss_killed": False,
                    "card_reward": 0.0,
                    "relic_reward": 0.0,
                    "gold_reward": 0.0,
                    "action_bonus": 0.0,
                    "end_turn_penalty": 0.0,
                    "enemy_strength_gained": 0.0,
                    "enemy_strength_gain_penalty": 0.0,
                    "reward_total": 0.0,
                }
            )

        # === TERMINAL REWARDS (highest priority) ===
        # Check for game over first
        if "GAME_OVER" in str(current_game.screen_type):
            # Determine victory vs defeat
            victory = self._is_victory(current_game)
            terminal_reward = self.calculate_terminal_reward(victory)
            reward += terminal_reward
            if info is not None:
                info["terminal_reward"] = terminal_reward
                info["reward_total"] = reward
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
            if info is not None:
                info["monster_count_last"] = len(last_monsters)
                info["monster_count_current"] = len(current_monsters)
                last_total_hp = sum(
                    m.current_hp for m in last_monsters if hasattr(m, "current_hp")
                )
                current_total_hp = sum(
                    m.current_hp for m in current_monsters if hasattr(m, "current_hp")
                )
                info["total_monster_hp_delta"] = last_total_hp - current_total_hp

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

            if info is not None:
                # Energy spent and block delta only make sense within the same turn.
                last_energy = self._safe_attr(last_game, 'player', 'energy', default=0)
                current_energy = self._safe_attr(current_game, 'player', 'energy', default=0)
                if hasattr(current_game, 'turn') and hasattr(last_game, 'turn') and current_game.turn == last_game.turn:
                    info["energy_spent"] = max(0, int(last_energy) - int(current_energy))
                    last_block = self._safe_attr(last_game, 'player', 'block', default=0)
                    current_block = self._safe_attr(current_game, 'player', 'block', default=0)
                    info["block_delta"] = int(current_block) - int(last_block)

            # Calculate combat reward
            combat_reward = self.calculate_combat_reward(
                current_game,
                damage_dealt=damage_dealt,
                monster_killed=monster_killed,
                all_monsters_killed=all_monsters_killed,
                hp_lost=hp_lost,
                turn_ended=turn_ended
            )
            reward += combat_reward
            if info is not None:
                info["combat_reward"] += combat_reward
                info["damage_dealt"] += damage_dealt
                info["hp_lost"] += hp_lost
                info["turn_ended"] = turn_ended
                info["monster_killed"] = info["monster_killed"] or monster_killed
                info["all_monsters_killed"] = info["all_monsters_killed"] or all_monsters_killed
        elif last_game.in_combat and not current_game.in_combat:
            combat_won = self._is_combat_victory(current_game)
            last_monsters = last_game.monsters if last_game.monsters else []
            had_alive_monsters = self._had_alive_monsters(last_monsters)
            finishing_damage = 0
            if had_alive_monsters:
                for monster in last_monsters:
                    if hasattr(monster, "current_hp") and monster.current_hp > 0:
                        finishing_damage += monster.current_hp
            combat_reward = self.calculate_combat_reward(
                last_game,
                damage_dealt=finishing_damage,
                monster_killed=combat_won and had_alive_monsters,
                all_monsters_killed=combat_won,
                hp_lost=0,
                turn_ended=False
            )
            reward += combat_reward
            if info is not None:
                info["combat_reward"] += combat_reward
                info["monster_count_last"] = len(last_monsters)
                info["monster_count_current"] = 0
                info["total_monster_hp_delta"] = finishing_damage
                info["damage_dealt"] += finishing_damage
                info["monster_killed"] = info["monster_killed"] or (combat_won and had_alive_monsters)
                info["all_monsters_killed"] = info["all_monsters_killed"] or combat_won
            if combat_won:
                elite_killed = self._is_elite_room(last_game)
                boss_killed = self._is_boss_room(last_game)
                if elite_killed or boss_killed:
                    progress_reward = self.calculate_progression_reward(
                        current_game,
                        floor_advanced=False,
                        elite_killed=elite_killed,
                        boss_killed=boss_killed
                    )
                    reward += progress_reward
                    if info is not None:
                        info["progress_reward"] += progress_reward
                        info["elite_killed"] = info["elite_killed"] or elite_killed
                        info["boss_killed"] = info["boss_killed"] or boss_killed

        # === PROGRESSION REWARDS ===
        # Floor advancement
        if hasattr(current_game, 'floor') and hasattr(last_game, 'floor'):
            floor_advanced = current_game.floor > last_game.floor
            if floor_advanced:
                progress_reward = self.calculate_progression_reward(
                    current_game,
                    floor_advanced=True,
                    elite_killed=False,  # TODO: detect elite kills
                    boss_killed=False    # TODO: detect boss kills
                )
                reward += progress_reward
                if info is not None:
                    info["progress_reward"] += progress_reward
                    info["floor_advanced"] = True

        # === ACQUISITION REWARDS ===
        # Card acquisition
        current_deck_size = len(current_game.deck) if current_game.deck else 0
        last_deck_size = len(last_game.deck) if last_game.deck else 0
        if current_deck_size > last_deck_size:
            card_reward = self._calculate_card_reward(current_game, last_game)
            reward += card_reward
            if info is not None:
                info["card_reward"] += card_reward
                info["acquisition_reward"] += card_reward
        if last_game.screen_type == ScreenType.CARD_REWARD and current_game.screen_type != ScreenType.CARD_REWARD:
            card_choice_reward = self._calculate_card_choice_reward(current_game, last_game)
            reward += card_choice_reward
            if info is not None:
                info["card_choice_reward"] += card_choice_reward

        # Relic acquisition
        current_relics = len(current_game.relics) if current_game.relics else 0
        last_relics = len(last_game.relics) if last_game.relics else 0
        if current_relics > last_relics:
            # Agent obtained a relic
            relic_reward = self.calculate_acquisition_reward(
                current_game,
                card_obtained=False,
                relic_obtained=True
            )
            reward += relic_reward
            if info is not None:
                info["relic_reward"] += relic_reward
                info["acquisition_reward"] += relic_reward

        # Gold acquisition (small reward)
        if hasattr(current_game, 'gold') and hasattr(last_game, 'gold'):
            gold_gained = current_game.gold - last_game.gold
            if gold_gained > 0:
                gold_reward = self.calculate_acquisition_reward(
                    current_game,
                    gold_obtained=gold_gained
                )
                reward += gold_reward
                if info is not None:
                    info["gold_reward"] += gold_reward
                    info["acquisition_reward"] += gold_reward

        # === ACTION-LEVEL SHAPING ===
        if action_context and current_game.in_combat and last_game.in_combat:
            action_name = action_context.get("action_name")
            had_play_options = bool(action_context.get("had_play_options", False))
            played_card_type = action_context.get("played_card_type")

            action_bonus = 0.0
            end_turn_penalty = 0.0
            enemy_strength_gain_penalty = 0.0

            if action_name == "PlayCardAction":
                # Small positive feedback for taking an action.
                action_bonus += 0.03
                if info is not None:
                    action_bonus += 0.02 * info.get("energy_spent", 0)
            elif action_name == "PotionAction":
                action_bonus += 0.02

            if action_name == "EndTurnAction" and had_play_options:
                end_turn_penalty = -0.2

            if action_name == "PlayCardAction" and played_card_type == "SKILL":
                strength_gained = self._calculate_enemy_strength_gain(last_game, current_game)
                if strength_gained > 0:
                    enemy_strength_gain_penalty = -min(
                        strength_gained * self.ENEMY_STRENGTH_GAIN_PENALTY,
                        self.ENEMY_STRENGTH_GAIN_CAP,
                    )
                    reward += enemy_strength_gain_penalty
                    if info is not None:
                        info["enemy_strength_gained"] += strength_gained
                        info["enemy_strength_gain_penalty"] += enemy_strength_gain_penalty

            if action_bonus or end_turn_penalty:
                reward += action_bonus + end_turn_penalty
                if info is not None:
                    info["action_bonus"] += action_bonus
                    info["end_turn_penalty"] += end_turn_penalty

        if info is not None:
            info["reward_total"] = reward

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

    def _calculate_card_reward(self, current_game: Game, last_game: Game) -> float:
        """
        Calculate reward for card acquisition using CARD_PRIORITY_LIST order.

        Called whenever a card is added to the deck (from any source).
        """
        if not current_game.deck:
            return 0.0
        last_uuids = {card.uuid for card in last_game.deck} if last_game.deck else set()
        new_cards = [card for card in current_game.deck if card.uuid not in last_uuids]
        if not new_cards:
            return 0.0

        reward = 0.0
        for card in new_cards:
            card_score = self._priority_score(card, current_game)
            # Scale base reward by heuristic score (-1..1); good cards > 0, bad cards < 0.
            card_reward = self.calculate_acquisition_reward(
                current_game,
                card_obtained=True,
                card_power_score=card_score,
                relic_obtained=False,
            )
            reward += card_reward

            if self._card_reward_debug:
                card_name = getattr(card, 'card_id', None) or getattr(card, 'name', 'Unknown')
                rarity = getattr(card, 'rarity', None)
                rarity_name = getattr(rarity, 'name', str(rarity)) if rarity else "UNKNOWN"
                logger.info(
                    "[CARD_REWARD_HEUR] card=%s rarity=%s score=%.3f reward=%.3f",
                    card_name,
                    rarity_name,
                    card_score,
                    card_reward,
                )
        return reward

    def _calculate_card_choice_reward(self, current_game: Game, last_game: Game) -> float:
        """
        Calculate reward for card choice using CARD_PRIORITY_LIST order.
        """
        screen = getattr(last_game, 'screen', None)
        candidates = getattr(screen, 'cards', None) if screen else None
        if not candidates:
            return 0.0

        # Track what was chosen (for logging only)
        last_uuids = {card.uuid for card in last_game.deck} if last_game.deck else set()
        new_cards = [card for card in current_game.deck if card.uuid not in last_uuids] if current_game.deck else []
        chosen_card = new_cards[0] if new_cards else None

        candidate_scores = [self._priority_score(card, last_game) for card in candidates]
        if chosen_card is not None:
            chosen_score = self._priority_score(chosen_card, last_game)
        else:
            chosen_score = self._skip_score(last_game)
        relative_score = self._relative_rank_score(chosen_score, candidate_scores)
        reward = self.CARD_CHOICE_RELATIVE_SCALE * relative_score

        if self._card_reward_debug:
            chosen_name = "SKIP" if chosen_card is None else (
                getattr(chosen_card, 'card_id', None) or getattr(chosen_card, 'name', 'Unknown')
            )
            candidate_entries = []
            for card in candidates:
                card_name = getattr(card, 'card_id', None) or getattr(card, 'name', 'Unknown')
                rarity = getattr(card, 'rarity', None)
                rarity_name = rarity.name if rarity else "UNKNOWN"
                candidate_entries.append(f"{card_name}({rarity_name})")
            logger.info(
                "[CARD_CHOICE_HEUR] chosen=%s rel_score=%.3f candidates=%s",
                chosen_name,
                relative_score,
                ", ".join(candidate_entries),
            )

        return reward

    def _get_priority(self, game: Game) -> Optional[Priority]:
        player_class = getattr(game, "character", None)
        return self._priority_by_class.get(player_class)

    def _priority_score(self, card, game: Game) -> float:
        """
        Score a card by its position in CARD_PRIORITY_LIST.

        Returns a score in [-1, 1], where 1 is best, 0 is "Skip" (if present),
        and negative values are below Skip.
        """
        priority = self._get_priority(game)
        if priority is None or not priority.CARD_PRIORITY_LIST:
            return 0.0

        priorities = priority.CARD_PRIORITIES
        total = max(len(priority.CARD_PRIORITY_LIST) - 1, 1)
        idx = priorities.get(getattr(card, "card_id", None), len(priority.CARD_PRIORITY_LIST))
        skip_idx = priorities.get("Skip", None)

        if skip_idx is None:
            return max(-1.0, min(1.0, 1.0 - (idx / total)))

        if idx <= skip_idx:
            denom = max(skip_idx, 1)
            return max(-1.0, min(1.0, 1.0 - (idx / denom)))

        denom = max(total - skip_idx, 1)
        return max(-1.0, min(1.0, -((idx - skip_idx) / denom)))

    def _skip_score(self, game: Game) -> float:
        priority = self._get_priority(game)
        if priority is None or "Skip" not in priority.CARD_PRIORITIES:
            return 0.0
        skip_idx = priority.CARD_PRIORITIES["Skip"]
        total = max(len(priority.CARD_PRIORITY_LIST) - 1, 1)
        if skip_idx <= 0:
            return 0.0
        return max(-1.0, min(1.0, 1.0 - (skip_idx / total)))

    @staticmethod
    def _get_power_amount(entity, power_id: str) -> int:
        powers = getattr(entity, "powers", []) or []
        for power in powers:
            if getattr(power, "power_id", None) == power_id:
                return getattr(power, "amount", 0) or 0
            if getattr(power, "power_name", None) == power_id:
                return getattr(power, "amount", 0) or 0
        return 0

    def _calculate_enemy_strength_gain(self, last_game: Game, current_game: Game) -> int:
        last_monsters = last_game.monsters if last_game.monsters else []
        current_monsters = current_game.monsters if current_game.monsters else []

        last_strengths = {}
        for idx, monster in enumerate(last_monsters):
            key = getattr(monster, "monster_index", None)
            if key is None:
                key = idx
            last_strengths[key] = self._get_power_amount(monster, "Strength")

        strength_gained = 0
        for idx, monster in enumerate(current_monsters):
            key = getattr(monster, "monster_index", None)
            if key is None:
                key = idx
            current_strength = self._get_power_amount(monster, "Strength")
            last_strength = last_strengths.get(key, 0)
            if current_strength > last_strength:
                strength_gained += (current_strength - last_strength)

        return strength_gained

    # DEPRECATED: Heuristic card scoring methods (no longer used - pure RL approach)
    # Kept for reference/backward compatibility
    @staticmethod
    def _relative_rank_score(chosen_score: float, scores: Iterable[float]) -> float:
        scores_list = list(scores)
        if not scores_list:
            return 0.0
        if len(scores_list) == 1:
            return 1.0

        scores_list.sort()
        lower = sum(1 for score in scores_list if score < chosen_score)
        equal = sum(1 for score in scores_list if score == chosen_score)

        if equal == 0:
            if chosen_score <= scores_list[0]:
                rank = 0.0
            elif chosen_score >= scores_list[-1]:
                rank = len(scores_list) - 1.0
            else:
                rank = float(lower)
        else:
            rank = lower + (equal - 1) / 2.0

        return (rank / (len(scores_list) - 1)) * 2.0 - 1.0

    # DEPRECATED: Heuristic card scoring (no longer used - pure RL approach)
    # Kept for reference/backward compatibility
    @staticmethod
    def _simple_card_score(self, card) -> float:
        rarity = getattr(card, 'rarity', None)
        rarity_score = {
            CardRarity.BASIC: 0.0,
            CardRarity.COMMON: 0.5,
            CardRarity.UNCOMMON: 1.0,
            CardRarity.RARE: 1.5,
            CardRarity.SPECIAL: 1.0,
            CardRarity.CURSE: -1.0,
        }.get(rarity, 0.0)

        upgrades = 1.0 if getattr(card, 'upgrades', 0) else 0.0
        damage, block = self._extract_card_damage_block(card)
        stats = float(damage) + float(block)

        cost = getattr(card, 'cost_for_turn', None)
        if cost is None:
            cost = getattr(card, 'cost', 0)
        try:
            cost_value = int(cost)
        except (TypeError, ValueError):
            cost_value = 1
        if cost_value < 0:
            cost_value = 1

        effective_cost = 0.5 if cost_value == 0 else cost_value
        efficiency = (stats / effective_cost) * 0.1

        return rarity_score + (upgrades * 0.2) + efficiency

    @staticmethod
    def _extract_card_damage_block(card) -> Tuple[float, float]:
        damage = 0
        block = 0
        if hasattr(card, 'properties') and card.properties:
            try:
                for prop in card.properties:
                    if hasattr(prop, 'damage'):
                        damage = getattr(prop, 'damage', 0)
                    if hasattr(prop, 'block'):
                        block = getattr(prop, 'block', 0)
            except (AttributeError, TypeError):
                pass

        if damage == 0 and hasattr(card, 'damage'):
            try:
                damage = card.damage
            except (AttributeError, TypeError):
                pass

        if block == 0 and hasattr(card, 'block'):
            try:
                block = card.block
            except (AttributeError, TypeError):
                pass

        return damage, block


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
