"""
Reward calculator for shaping rewards in RL training.

Provides dense reward signals for combat survival, damage dealt, game progression, etc.
"""

import math
from typing import Optional
from spirecomm.spire.game import Game


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
    DAMAGE_REWARD_SCALE = 0.1
    KILL_REWARD = 10.0
    ALL_LETHAL_BONUS = 50.0
    HP_LOSS_PENALTY = 5.0
    TURN_END_PENALTY = -0.1

    # Progression reward weights
    FLOOR_REWARD_SCALE = 1.0
    ELITE_REWARD = 30.0
    BOSS_REWARD = 100.0

    # Acquisition reward weights
    CARD_REWARD_BASE = 5.0
    RELIC_REWARD = 20.0
    GOLD_REWARD_SCALE = 0.01

    # Terminal rewards
    VICTORY_REWARD = 1000.0
    DEFEAT_PENALTY = -500.0

    def __init__(self):
        """Initialize reward calculator with tracking."""
        self.reset()

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
        reward += min(damage_dealt * self.DAMAGE_REWARD_SCALE, 10.0)
        self.total_damage_dealt += damage_dealt
        if monster_killed:
            reward += self.KILL_REWARD
            self.monsters_killed += 1
        if all_monsters_killed:
            reward += self.ALL_LETHAL_BONUS
        if hp_lost > 0:
            reward -= self.HP_LOSS_PENALTY * hp_lost
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
            reward += floors_gained * self.FLOOR_REWARD_SCALE * game.floor
            self.last_floor = game.floor
        if elite_killed:
            reward += self.ELITE_REWARD
            self.elites_killed += 1
        if boss_killed:
            reward += self.BOSS_REWARD
            self.bosses_killed += 1
        return reward

    def calculate_acquisition_reward(self, game: Game, card_obtained: bool = False,
                                     card_power_score: int = 1,
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
            if (hasattr(current_game, 'player') and current_game.player is not None and
                hasattr(last_game, 'player') and last_game.player is not None):

                current_hp = current_game.player.current_hp if hasattr(current_game.player, 'current_hp') else 0
                last_hp = last_game.player.current_hp if hasattr(last_game.player, 'current_hp') else 0

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
            # Agent obtained a card
            # Simple heuristic: assume average power score of 2
            reward += self.calculate_acquisition_reward(
                current_game,
                card_obtained=True,
                card_power_score=2,  # TODO: calculate actual card power
                relic_obtained=False
            )

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
        if (hasattr(game, 'player') and game.player is not None and
            hasattr(game.player, 'current_hp') and game.player.current_hp > 0):
            return True

        # Default: assume defeat
        return False


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
