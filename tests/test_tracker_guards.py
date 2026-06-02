from types import SimpleNamespace

from spirecomm.ai.tracker import GameTracker


def test_game_tracker_record_game_over_accepts_numeric_string_hp_fields():
    tracker = GameTracker()
    final_state = SimpleNamespace(
        floor=12,
        act=1,
        score=345,
        current_hp="20",
        max_hp="80",
    )

    tracker.record_game_over(victory=False, final_state=final_state)

    assert tracker.current_hp_at_death == 20
    assert tracker.death_hp_pct == 0.25
