import pytest
from types import SimpleNamespace

from spirecomm.communication.coordinator import Coordinator
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.screen import ScreenType


def test_startup_state_wait_is_longer_than_in_game_stuck_guard():
    assert Coordinator.STATE_WAIT_SECONDS == 2.0
    assert Coordinator.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT >= 45
    assert Coordinator.IN_GAME_CONSECUTIVE_TIMEOUT_LIMIT == 10
    assert (
        Coordinator.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT
        > Coordinator.IN_GAME_CONSECUTIVE_TIMEOUT_LIMIT
    )


def test_startup_wait_requests_state_when_main_menu_does_not_push_initial_state():
    coordinator = object.__new__(Coordinator)
    coordinator.game_is_ready = False
    coordinator.in_game = False
    coordinator.last_game_state = None
    coordinator.pending_seed = None
    coordinator.game_over_state = None
    coordinator.STARTUP_MAX_WAIT_ATTEMPTS = 3
    coordinator.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT = 3
    sent_messages = []

    coordinator.clear_actions = lambda: None
    coordinator.receive_game_state_update = (
        lambda block=False, perform_callbacks=True: False
    )
    coordinator.send_message = (
        lambda message, wait_for_response=True: sent_messages.append(
            (message, wait_for_response)
        )
    )

    with pytest.raises(Exception, match="Communication Mod not responding"):
        coordinator.play_one_game(PlayerClass.IRONCLAD, ascension_level=0)

    assert ("state", False) in sent_messages


def test_idle_in_game_wait_requests_state_for_event_result_pages():
    coordinator = object.__new__(Coordinator)
    coordinator.last_game_state = SimpleNamespace(screen_type=ScreenType.EVENT)
    coordinator.action_queue = []
    sent_messages = []
    coordinator.send_message = (
        lambda message, wait_for_response=True: sent_messages.append(
            (message, wait_for_response)
        )
    )

    coordinator._request_state_during_idle_wait(1)

    assert sent_messages == [("state", False)]
