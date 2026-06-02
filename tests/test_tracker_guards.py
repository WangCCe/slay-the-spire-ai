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


def test_game_tracker_record_game_over_accepts_decimal_string_hp_fields():
    tracker = GameTracker()
    final_state = SimpleNamespace(
        floor=12,
        act=1,
        score=345,
        current_hp="20.0",
        max_hp="80.0",
    )

    tracker.record_game_over(victory=False, final_state=final_state)

    assert tracker.current_hp_at_death == 20
    assert tracker.death_hp_pct == 0.25


def test_game_tracker_record_game_over_defaults_nonfinite_hp_fields():
    tracker = GameTracker()
    final_state = SimpleNamespace(
        floor=12,
        act=1,
        score=345,
        current_hp=float("inf"),
        max_hp=float("inf"),
    )

    tracker.record_game_over(victory=False, final_state=final_state)

    assert tracker.current_hp_at_death == 0
    assert tracker.death_hp_pct == 0.0


def test_game_tracker_end_combat_accepts_numeric_string_hp_and_turn_fields():
    tracker = GameTracker()

    tracker.start_combat(
        floor=4,
        act=1,
        room_type="monster",
        start_turn="2",
        current_hp="70",
    )
    tracker.end_combat(hp_remaining="55", max_hp="80", end_turn="4")

    combat = tracker.combats[0]
    assert combat["hp_at_start"] == 70
    assert combat["hp_at_end"] == 55
    assert combat["turns"] == 3
    assert tracker.total_hp_loss_accumulated == 15


def test_game_tracker_end_combat_defaults_nonfinite_hp_and_turn_fields():
    tracker = GameTracker()

    tracker.start_combat(
        floor=4,
        act=1,
        room_type="monster",
        start_turn=float("inf"),
        current_hp=float("inf"),
    )
    tracker.end_combat(hp_remaining=float("inf"), max_hp=80, end_turn=float("inf"))

    combat = tracker.combats[0]
    assert combat["hp_at_start"] == 0
    assert combat["hp_at_end"] == 0
    assert combat["turns"] == 1
    assert tracker.total_hp_loss_accumulated == 0


def test_game_tracker_end_combat_accepts_decimal_string_hp_and_turn_fields():
    tracker = GameTracker()

    tracker.start_combat(
        floor=4,
        act=1,
        room_type="monster",
        start_turn="2.0",
        current_hp="70.0",
    )
    tracker.end_combat(hp_remaining="55.0", max_hp="80.0", end_turn="4.0")

    combat = tracker.combats[0]
    assert combat["hp_at_start"] == 70
    assert combat["hp_at_end"] == 55
    assert combat["turns"] == 3
    assert tracker.total_hp_loss_accumulated == 15
