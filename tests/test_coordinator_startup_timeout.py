from spirecomm.communication.coordinator import Coordinator


def test_startup_state_wait_is_longer_than_in_game_stuck_guard():
    assert Coordinator.STATE_WAIT_SECONDS == 2.0
    assert Coordinator.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT >= 45
    assert Coordinator.IN_GAME_CONSECUTIVE_TIMEOUT_LIMIT == 10
    assert (
        Coordinator.STARTUP_CONSECUTIVE_TIMEOUT_LIMIT
        > Coordinator.IN_GAME_CONSECUTIVE_TIMEOUT_LIMIT
    )
