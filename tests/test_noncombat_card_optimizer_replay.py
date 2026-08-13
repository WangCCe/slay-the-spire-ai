from __future__ import annotations

import copy

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_optimizer_replay as replay
from analysis_scripts.noncombat_card_acceptance_objective import build_card_acceptance_policy_terms
from analysis_scripts.noncombat_state_conditioned_policy_input import HASH_DIM


def _episode(bootstrap, *, seed: int = 11):
    state = torch.zeros(HASH_DIM, dtype=torch.float32)
    state[3] = 1.5
    candidates = (
        {"action_id": "skip", "kind": "skip"},
        {"action_id": "take", "kind": "take"},
    )
    candidate_features = torch.zeros((2, HASH_DIM), dtype=torch.float32)
    candidate_features[0, 4] = 1.0
    candidate_features[1, 5] = 2.0
    output = runtime.forward_card_policy(
        bootstrap,
        arm="candidate",
        state_features=state,
        candidate_features=candidate_features,
        candidates=candidates,
    )
    terms = build_card_acceptance_policy_terms(
        output.family_logits,
        output.conditional_logits,
        candidates,
        "take",
        category="card_reward",
    )
    decision = runtime.ArmRolloutDecision(
        arm="candidate",
        category="card_reward",
        decision_id=f"candidate:seed-{seed}:decision-0",
        decision_index=0,
        selected_action_id="take",
        state_features=state,
        card_terms=terms,
        diagnostic={"not": "serialized"},
        candidate_features=candidate_features,
        candidates=candidates,
    )
    return runtime.ArmEpisodeRollout(
        arm="candidate",
        seed=seed,
        trajectory_id=f"candidate:seed-{seed}",
        decisions=(decision,),
        transitions=({"not": "serialized"},),
        rewards=(0.25,),
        final_snapshot={"terminal": True, "not": "serialized"},
        floor_progress=0.25,
        terminal_victory=0,
        unsupported_reason=None,
    )


def _episode_with_noncard_context(bootstrap, *, seed: int = 12):
    episode = _episode(bootstrap, seed=seed)
    state = torch.zeros(HASH_DIM, dtype=torch.float32)
    candidates = (
        {"action_id": "left", "kind": "route"},
        {"action_id": "right", "kind": "route"},
    )
    candidate_features = torch.zeros((2, HASH_DIM), dtype=torch.float32)
    candidate_features[0, 7] = 1.0
    candidate_features[1, 8] = 2.0
    decision = runtime.ArmRolloutDecision(
        arm="candidate",
        category="route",
        decision_id=f"candidate:seed-{seed}:decision-1",
        decision_index=1,
        selected_action_id="right",
        state_features=state,
        card_terms=None,
        diagnostic={"not": "serialized"},
        candidate_features=candidate_features,
        candidates=candidates,
    )
    return runtime.ArmEpisodeRollout(
        arm=episode.arm,
        seed=seed,
        trajectory_id=episode.trajectory_id,
        decisions=episode.decisions + (decision,),
        transitions=episode.transitions + ({"not": "serialized"},),
        rewards=episode.rewards + (0.5,),
        final_snapshot=episode.final_snapshot,
        floor_progress=episode.floor_progress,
        terminal_victory=episode.terminal_victory,
        unsupported_reason=episode.unsupported_reason,
    )


def _generator_states(bootstrap):
    return {
        name: generator.get_state().clone()
        for name, generator in bootstrap.generators.items()
    }


def test_replay_round_trip_is_byte_exact_and_terms_are_rebuilt() -> None:
    bootstrap = runtime.build_matched_bootstrap()
    encoded = replay.encode_replay(
        (_episode_with_noncard_context(bootstrap),),
        generator_states=_generator_states(bootstrap),
    )

    decoded = replay.decode_replay(encoded.stored, encoded.binding)
    second = replay.encode_replay(
        decoded.episodes, generator_states=decoded.generator_states
    )
    rebuilt = replay.rebuild_episode_terms(bootstrap, decoded.episodes)

    assert second == encoded
    assert decoded.episodes[0].decisions[0].card_terms is None
    assert rebuilt[0].decisions[0].card_terms.selected_action_id == "take"
    assert rebuilt[0].decisions[1].card_terms is None
    assert rebuilt[0].decisions[1].selected_action_id == "right"
    assert torch.equal(
        rebuilt[0].decisions[1].candidate_features,
        decoded.episodes[0].decisions[1].candidate_features,
    )
    assert rebuilt[0].transitions == ({}, {})


def test_replay_rejects_stored_byte_drift() -> None:
    bootstrap = runtime.build_matched_bootstrap()
    encoded = replay.encode_replay(
        (_episode(bootstrap),), generator_states=_generator_states(bootstrap)
    )
    drifted = encoded.stored[:-1] + bytes([encoded.stored[-1] ^ 1])

    with pytest.raises(replay.CardOptimizerReplayBlocked, match="stored hash"):
        replay.decode_replay(drifted, encoded.binding)


def test_replay_rejects_declared_size_above_bound() -> None:
    bootstrap = runtime.build_matched_bootstrap()
    encoded = replay.encode_replay(
        (_episode(bootstrap),), generator_states=_generator_states(bootstrap)
    )
    binding = copy.deepcopy(encoded.binding)
    binding["canonical_size_bytes"] = replay.MAX_CANONICAL_BYTES + 1

    with pytest.raises(replay.CardOptimizerReplayBlocked, match="canonical_size"):
        replay.decode_replay(encoded.stored, binding)


def test_replay_rejects_decision_order_drift_before_encoding() -> None:
    bootstrap = runtime.build_matched_bootstrap()
    episode = _episode(bootstrap)
    decision = episode.decisions[0]
    drifted_decision = runtime.ArmRolloutDecision(
        arm=decision.arm,
        category=decision.category,
        decision_id=decision.decision_id,
        decision_index=1,
        selected_action_id=decision.selected_action_id,
        state_features=decision.state_features,
        card_terms=decision.card_terms,
        diagnostic=decision.diagnostic,
        candidate_features=decision.candidate_features,
        candidates=decision.candidates,
    )
    drifted = runtime.ArmEpisodeRollout(
        arm=episode.arm,
        seed=episode.seed,
        trajectory_id=episode.trajectory_id,
        decisions=(drifted_decision,),
        transitions=episode.transitions,
        rewards=episode.rewards,
        final_snapshot=episode.final_snapshot,
        floor_progress=episode.floor_progress,
        terminal_victory=episode.terminal_victory,
        unsupported_reason=episode.unsupported_reason,
    )

    with pytest.raises(replay.CardOptimizerReplayBlocked, match="order"):
        replay.encode_replay(
            (drifted,), generator_states=_generator_states(bootstrap)
        )
