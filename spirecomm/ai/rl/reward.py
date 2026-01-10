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
