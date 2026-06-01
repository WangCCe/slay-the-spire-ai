from types import SimpleNamespace

from spirecomm.communication.action import PotionAction


def test_potion_action_execute_uses_get_real_potions_without_raw_potions():
    sent_messages = []
    potion = SimpleNamespace(potion_id="Strength Potion")
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(get_real_potions=lambda: [potion]),
        send_message=sent_messages.append,
    )

    PotionAction(True, potion=potion).execute(coordinator)

    assert sent_messages == ["potion use 0"]
