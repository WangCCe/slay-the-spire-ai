from types import SimpleNamespace

import pytest

from spirecomm.communication.action import CombatRewardAction
from spirecomm.spire.screen import ScreenType


def test_combat_reward_action_rejects_namespaced_string_potion_when_slots_are_full():
    sent_messages = []
    potion_reward = SimpleNamespace(reward_type="RewardType.POTION")

    def send_message(message, wait_for_response=True):
        sent_messages.append((message, wait_for_response))

    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(
            screen_type=ScreenType.COMBAT_REWARD,
            screen=SimpleNamespace(rewards=[potion_reward]),
            are_potions_full=lambda: True,
        ),
        game_is_ready=True,
        send_message=send_message,
    )

    with pytest.raises(Exception, match="Cannot choose potion reward"):
        CombatRewardAction(potion_reward).execute(coordinator)

    assert sent_messages == []
