from __future__ import annotations

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_scorer_optimizer as scorer
from analysis_scripts.noncombat_card_acceptance_objective import build_card_acceptance_policy_terms
from analysis_scripts.noncombat_state_conditioned_policy_input import HASH_DIM


def _warm_full_optimizer(bootstrap):
    optimizer = runtime.build_candidate_card_optimizer(bootstrap)
    for parameter in optimizer.param_groups[0]["params"]:
        parameter.grad = torch.full_like(parameter, 0.125)
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    return optimizer


def _objective(bootstrap):
    state = torch.zeros(HASH_DIM, dtype=torch.float32)
    candidates = (
        {"action_id": "skip", "kind": "skip"},
        {"action_id": "take", "kind": "take"},
    )
    features = torch.zeros((2, HASH_DIM), dtype=torch.float32)
    features[0, 3] = 1.0
    features[1, 4] = 2.0
    output = runtime.forward_card_policy(
        bootstrap,
        arm="candidate",
        state_features=state,
        candidate_features=features,
        candidates=candidates,
    )
    terms = build_card_acceptance_policy_terms(
        output.family_logits,
        output.conditional_logits,
        candidates,
        "take",
        category="card_reward",
    )
    return runtime.build_arm_card_reward_objective(((terms, 1.0),))


def test_scorer_optimizer_selects_exact_names_and_moments() -> None:
    bootstrap = runtime.build_matched_bootstrap()
    full = _warm_full_optimizer(bootstrap)

    selected = scorer.build_scorer_optimizer(bootstrap, full)

    assert selected.parameter_names == scorer.SCORER_PARAMETER_NAMES
    assert tuple(
        parameter for name, parameter in runtime._arm_named_trainable_parameters(
            bootstrap, arm="candidate"
        ) if ".scorer." in name
    ) == selected.parameters
    assert len(selected.optimizer.state) == 4
    for parameter in selected.parameters:
        assert torch.equal(
            selected.optimizer.state[parameter]["exp_avg"],
            full.state[parameter]["exp_avg"],
        )
        assert torch.equal(
            selected.optimizer.state[parameter]["exp_avg_sq"],
            full.state[parameter]["exp_avg_sq"],
        )
        assert torch.equal(
            selected.optimizer.state[parameter]["step"],
            full.state[parameter]["step"],
        )


def test_scorer_optimizer_rejects_full_parameter_order_drift() -> None:
    bootstrap = runtime.build_matched_bootstrap()
    full = _warm_full_optimizer(bootstrap)
    full.param_groups[0]["params"][0], full.param_groups[0]["params"][1] = (
        full.param_groups[0]["params"][1],
        full.param_groups[0]["params"][0],
    )

    with pytest.raises(scorer.ScorerOptimizerBlocked, match="ownership"):
        scorer.build_scorer_optimizer(bootstrap, full)


def test_scorer_optimizer_rejects_missing_source_moment() -> None:
    bootstrap = runtime.build_matched_bootstrap()
    full = _warm_full_optimizer(bootstrap)
    scorer_parameter = next(
        parameter
        for name, parameter in runtime._arm_named_trainable_parameters(
            bootstrap, arm="candidate"
        )
        if name == scorer.SCORER_PARAMETER_NAMES[0]
    )
    del full.state[scorer_parameter]

    with pytest.raises(scorer.ScorerOptimizerBlocked, match="moment is missing"):
        scorer.build_scorer_optimizer(bootstrap, full)


def test_scorer_step_preserves_hidden_parameter_bytes() -> None:
    bootstrap = runtime.build_matched_bootstrap()
    full = _warm_full_optimizer(bootstrap)
    selected = scorer.build_scorer_optimizer(bootstrap, full)
    before = scorer.candidate_hidden_parameter_bytes(bootstrap)
    guarded_before = scorer.candidate_guarded_model_bytes(bootstrap)

    runtime.apply_arm_optimizer_step(
        selected.optimizer,
        _objective(bootstrap),
        parameters=selected.parameters,
        parameter_names=selected.parameter_names,
    )

    assert scorer.candidate_hidden_parameter_bytes(bootstrap) == before
    assert scorer.candidate_guarded_model_bytes(bootstrap) == guarded_before
