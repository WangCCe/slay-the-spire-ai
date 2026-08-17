import pytest
import torch

from analysis_scripts.reconstruct_combat_rl_replay_checkpoint import (
    TENSOR_FIELDS,
    _reconstruct_replay,
)


def _payload(values, total_steps, *, truncated):
    count = len(values)
    replay = {
        "schema_version": 1,
        "buffer_size": 100,
        "continuous_dim": 1,
        "action_dim": 1,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
        "transition_count": count,
        "source_transition_count": total_steps,
        "truncated": truncated,
    }
    vector_fields = {"actions", "rewards", "dones"}
    for field in TENSOR_FIELDS:
        dtype = torch.float32
        if field in {
            "card_ids",
            "potion_ids",
            "relic_ids",
            "actions",
            "next_card_ids",
            "next_potion_ids",
            "next_relic_ids",
        }:
            dtype = torch.int64
        elif field in {"dones", "action_masks", "next_action_masks"}:
            dtype = torch.bool
        tensor = torch.tensor(values, dtype=dtype)
        replay[field] = tensor if field in vector_fields else tensor[:, None]
    return {"total_steps": total_steps, "replay_buffer_state_dict": replay}


def test_reconstructs_overlapping_chronological_replays():
    replay, details = _reconstruct_replay(
        _payload([0, 1, 2, 3], 4, truncated=False),
        _payload([2, 3, 4, 5], 6, truncated=True),
    )

    assert replay["transition_count"] == 6
    assert replay["truncated"] is False
    assert replay["actions"].tolist() == [0, 1, 2, 3, 4, 5]
    assert details["overlap_transition_count"] == 2
    assert details["appended_transition_count"] == 2


def test_rejects_any_tensor_overlap_mismatch():
    prefix = _payload([0, 1, 2, 3], 4, truncated=False)
    suffix = _payload([2, 3, 4, 5], 6, truncated=True)
    suffix["replay_buffer_state_dict"]["rewards"][0] = 99

    with pytest.raises(ValueError, match="Replay overlap mismatch: rewards"):
        _reconstruct_replay(prefix, suffix)
