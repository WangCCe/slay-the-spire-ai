from types import SimpleNamespace

from spirecomm.communication.action import PlayCardAction


def test_play_card_action_requests_state_when_uuid_card_left_hand():
    stale_card = SimpleNamespace(uuid="gone-card", name="Burning Pact")
    current_card = SimpleNamespace(uuid="other-card", name="Strike")
    sent_messages = []
    coordinator = SimpleNamespace(
        last_game_state=SimpleNamespace(hand=[current_card]),
        send_message=sent_messages.append,
    )

    PlayCardAction(card=stale_card, card_index=0).execute(coordinator)

    assert sent_messages == ["state"]
