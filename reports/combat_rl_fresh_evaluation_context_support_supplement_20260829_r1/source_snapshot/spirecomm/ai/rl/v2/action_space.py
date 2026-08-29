"""
Action space constants and helpers for RL v2.
"""

from dataclasses import dataclass


TARGET_SLOTS = 6  # 0=self/aoe/none, 1-5=monster targets

MAX_CARD_SLOTS = 10
MAX_POTION_SLOTS = 5
MAX_REWARD_CHOICES = 5
MAX_MAP_CHOICES = 6
MAX_EVENT_CHOICES = 6
MAX_SHOP_CHOICES = 15
MAX_REST_OPTIONS = 6

PLAY_CARD_OFFSET = 0
PLAY_CARD_COUNT = MAX_CARD_SLOTS * TARGET_SLOTS  # 60

USE_POTION_OFFSET = PLAY_CARD_OFFSET + PLAY_CARD_COUNT  # 60
USE_POTION_COUNT = MAX_POTION_SLOTS * TARGET_SLOTS  # 30

END_TURN_ACTION = USE_POTION_OFFSET + USE_POTION_COUNT  # 90

REWARD_OFFSET = END_TURN_ACTION + 1  # 91
REWARD_COUNT = MAX_REWARD_CHOICES  # 5

MAP_OFFSET = REWARD_OFFSET + REWARD_COUNT  # 96
MAP_COUNT = MAX_MAP_CHOICES  # 6

EVENT_OFFSET = MAP_OFFSET + MAP_COUNT  # 102
EVENT_COUNT = MAX_EVENT_CHOICES  # 6

SHOP_OFFSET = EVENT_OFFSET + EVENT_COUNT  # 108
SHOP_COUNT = MAX_SHOP_CHOICES  # 15

REST_OFFSET = SHOP_OFFSET + SHOP_COUNT  # 123
REST_COUNT = MAX_REST_OPTIONS  # 6

SYSTEM_OFFSET = REST_OFFSET + REST_COUNT  # 129
SYSTEM_COUNT = 4  # Confirm, Cancel, Leave, Proceed

ACTION_DIM = SYSTEM_OFFSET + SYSTEM_COUNT  # 133


@dataclass(frozen=True)
class SystemActionIndex:
    confirm: int = SYSTEM_OFFSET
    cancel: int = SYSTEM_OFFSET + 1
    leave: int = SYSTEM_OFFSET + 2
    proceed: int = SYSTEM_OFFSET + 3


SYSTEM_ACTIONS = SystemActionIndex()


def encode_play_card(card_slot: int, target_index: int) -> int:
    return PLAY_CARD_OFFSET + (card_slot * TARGET_SLOTS) + target_index


def encode_use_potion(potion_slot: int, target_index: int) -> int:
    return USE_POTION_OFFSET + (potion_slot * TARGET_SLOTS) + target_index
