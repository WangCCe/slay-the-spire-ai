from __future__ import annotations

from types import SimpleNamespace

import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_optimizer_replay as replay
from analysis_scripts import noncombat_card_scorer_optimizer_replay_ablation as ablation
from analysis_scripts.noncombat_card_acceptance_objective import build_card_acceptance_policy_terms
from analysis_scripts.noncombat_state_conditioned_policy_input import HASH_DIM


def _warm_entry():
    bootstrap = runtime.build_matched_bootstrap()
    optimizer = runtime.build_candidate_card_optimizer(bootstrap)
    for step in range(4):
        for index, parameter in enumerate(optimizer.param_groups[0]["params"]):
            parameter.grad = torch.full_like(parameter, (step + 1) * (index + 1) / 1000)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
    return bootstrap, optimizer


def _clone(bootstrap, optimizer):
    cloned_bootstrap = runtime.restore_paired_bootstrap(
        runtime.encode_paired_bootstrap(bootstrap)
    )
    cloned_optimizer = runtime.build_candidate_card_optimizer(cloned_bootstrap)
    runtime.restore_optimizer_state(
        cloned_optimizer, runtime.encode_optimizer_state(optimizer)
    )
    return cloned_bootstrap, cloned_optimizer


def _context(seed: int):
    state = torch.zeros(HASH_DIM, dtype=torch.float32)
    state[seed % HASH_DIM] = 1.0 + (seed % 7) / 10
    candidates = (
        {"action_id": "skip", "kind": "skip"},
        {"action_id": "take", "kind": "take"},
    )
    features = torch.zeros((2, HASH_DIM), dtype=torch.float32)
    features[0, (seed + 3) % HASH_DIM] = 1.0
    features[1, (seed + 5) % HASH_DIM] = 1.5
    return state, candidates, features


def _episodes(bootstrap):
    episodes = []
    for offset in range(64):
        seed = 1000 + offset
        state, candidates, features = _context(seed)
        output = runtime.forward_card_policy(
            bootstrap,
            arm="candidate",
            state_features=state,
            candidate_features=features,
            candidates=candidates,
        )
        selected = "take" if offset % 3 else "skip"
        terms = build_card_acceptance_policy_terms(
            output.family_logits,
            output.conditional_logits,
            candidates,
            selected,
            category="card_reward",
        )
        decision = runtime.ArmRolloutDecision(
            arm="candidate",
            category="card_reward",
            decision_id=f"candidate:seed-{seed}:decision-0",
            decision_index=0,
            selected_action_id=selected,
            state_features=state,
            card_terms=terms,
            diagnostic={},
            candidate_features=features,
            candidates=candidates,
        )
        episodes.append(
            runtime.ArmEpisodeRollout(
                arm="candidate",
                seed=seed,
                trajectory_id=f"candidate:seed-{seed}",
                decisions=(decision,),
                transitions=({},),
                rewards=((offset % 11) / 10,),
                final_snapshot={"terminal": True},
                floor_progress=(offset % 11) / 10,
                terminal_victory=int(offset == 63),
                unsupported_reason=None,
            )
        )
    return tuple(episodes)


def _probe_rows():
    rows = []
    for index, seed in enumerate(range(2001, 2176)):
        state, candidates, features = _context(seed)
        rows.append(
            SimpleNamespace(
                seed=seed,
                decision_index=index,
                state_features=state,
                candidate_features=features,
                candidates=candidates,
                target_action_id="take",
                target_family="take",
            )
        )
    return tuple(rows)


def test_decoded_replay_exactly_reproduces_full_update_and_freezes_hidden() -> None:
    entry_bootstrap, entry_optimizer = _warm_entry()
    source_episodes = _episodes(entry_bootstrap)
    generator_states = {
        name: generator.get_state().clone()
        for name, generator in entry_bootstrap.generators.items()
    }
    encoded = replay.encode_replay(
        source_episodes, generator_states=generator_states
    )
    decoded = replay.decode_replay(encoded.stored, encoded.binding)

    historical_bootstrap, historical_optimizer = _clone(
        entry_bootstrap, entry_optimizer
    )
    replay.apply_generator_states(historical_bootstrap, decoded.generator_states)
    historical_episodes = replay.rebuild_episode_terms(
        historical_bootstrap, decoded.episodes
    )
    runtime.apply_candidate_cross_fitted_chunk_update_exploratory(
        historical_bootstrap, historical_optimizer, historical_episodes
    )

    full_bootstrap, full_optimizer = _clone(entry_bootstrap, entry_optimizer)
    scorer_bootstrap, scorer_source_optimizer = _clone(
        entry_bootstrap, entry_optimizer
    )
    completed = ablation.apply_decoded_replay_ablation(
        full_bootstrap=full_bootstrap,
        full_optimizer=full_optimizer,
        scorer_bootstrap=scorer_bootstrap,
        scorer_source_optimizer=scorer_source_optimizer,
        decoded=decoded,
        expected_full_bootstrap=runtime.encode_paired_bootstrap(
            historical_bootstrap
        ),
        expected_full_optimizer=runtime.encode_optimizer_state(
            historical_optimizer
        ),
        probe_rows=_probe_rows(),
    )

    assert completed.telemetry["reproduction"] == {
        "bootstrap_exact": True,
        "exact": True,
        "optimizer_exact": True,
    }
    assert completed.telemetry["scorer_hidden_exact"] is True
    assert completed.telemetry["scorer_guarded_models_exact"] is True
    assert completed.telemetry["downstream_authority"] == ablation.FALSE_AUTHORITY
    assert len(completed.full_checkpoint) > 0
    assert len(completed.scorer_checkpoint) > 0


def test_retained_tv_gate_is_fixed_at_eighty_percent() -> None:
    def summary(mean):
        return {"joint_total_variation": {"mean": mean}}

    below = ablation.classify_result(
        reproduction_exact=True,
        hidden_exact=True,
        guarded_exact=True,
        branch_coverage=True,
        full_summary=summary(0.01),
        scorer_summary=summary(0.0079),
    )
    boundary = ablation.classify_result(
        reproduction_exact=True,
        hidden_exact=True,
        guarded_exact=True,
        branch_coverage=True,
        full_summary=summary(0.01),
        scorer_summary=summary(0.008),
    )

    assert below["verdict"] == "scorer_only_optimizer_not_ready"
    assert boundary["verdict"] == "ready_to_propose_four_step_scorer_optimizer_ablation"
