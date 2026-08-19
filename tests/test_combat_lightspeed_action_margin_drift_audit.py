import numpy as np

from analysis_scripts.combat_lightspeed_action_margin_drift_audit import (
    action_family,
    summarize_candidate_drift,
)


def test_action_family_covers_rl_v2_ranges():
    assert action_family(0) == "play_card"
    assert action_family(59) == "play_card"
    assert action_family(60) == "use_potion"
    assert action_family(89) == "use_potion"
    assert action_family(90) == "end_turn"
    assert action_family(91) == "reward"
    assert action_family(96) == "map"
    assert action_family(102) == "event"
    assert action_family(108) == "shop"
    assert action_family(123) == "rest"
    assert action_family(129) == "system"


def test_drift_summary_tracks_margin_and_family_flips():
    parent_q = np.full((3, 133), -np.inf, dtype=np.float32)
    candidate_q = np.full((3, 133), -np.inf, dtype=np.float32)
    masks = np.zeros((3, 133), dtype=bool)
    masks[:, [0, 60, 90]] = True

    parent_q[0, [0, 60, 90]] = [4.0, 3.0, 2.0]
    candidate_q[0, [0, 60, 90]] = [3.0, 3.5, 2.0]
    parent_q[1, [0, 60, 90]] = [1.0, 5.0, 2.0]
    candidate_q[1, [0, 60, 90]] = [1.0, 6.0, 2.0]
    parent_q[2, [0, 60, 90]] = [2.0, 1.0, 4.0]
    candidate_q[2, [0, 60, 90]] = [4.5, 1.0, 4.0]

    summary = summarize_candidate_drift(
        parent_q,
        candidate_q,
        masks,
        battle_indices=np.asarray([0, 6, 9]),
    )

    assert summary["transition_count"] == 3
    assert summary["action_disagreement_count"] == 2
    assert summary["action_disagreement_rate"] == 2 / 3
    assert summary["family_flip_counts"] == {
        "end_turn->play_card": 1,
        "play_card->use_potion": 1,
    }
    assert summary["by_battle_index"]["0"]["action_disagreement_rate"] == 1.0
    assert summary["by_battle_index"]["6"]["action_disagreement_rate"] == 0.0
    assert summary["parent_margin"]["mean"] == 2.0
    assert summary["parent_margin_when_disagreeing"]["mean"] == 1.5
