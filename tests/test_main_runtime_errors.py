from main import is_unrecoverable_run_error


def test_stuck_game_error_is_unrecoverable():
    assert is_unrecoverable_run_error(
        Exception(
            "Game appears stuck (no state update for 20 seconds). "
            "Last action may have caused the game to hang."
        )
    )


def test_communication_timeout_error_is_unrecoverable():
    assert is_unrecoverable_run_error(
        Exception("Communication Mod not responding (timeout after 10 attempts)")
    )


def test_generic_run_error_can_continue():
    assert not is_unrecoverable_run_error(Exception("temporary reward parsing issue"))
