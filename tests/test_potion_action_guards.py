from types import SimpleNamespace

from spirecomm.communication.action import PotionAction, WaitAction


def test_potion_action_execute_uses_get_real_potions_without_raw_potions():
    sent_messages = []
    queued_actions = []
    potion = SimpleNamespace(potion_id="Strength Potion")
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(get_real_potions=lambda: [potion]),
        send_message=sent_messages.append,
        add_action_to_queue=queued_actions.append,
    )

    PotionAction(True, potion=potion).execute(coordinator)

    assert sent_messages == ["potion use 0"]
    assert len(queued_actions) == 1
    assert isinstance(queued_actions[0], WaitAction)
    assert queued_actions[0].timeout == 1
