from __future__ import annotations

import copy
import hashlib
import random
from dataclasses import replace

import pytest
import torch

import analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime as runtime
import analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment as control
import analysis_scripts.noncombat_hierarchical_simulator_learning_runtime as consumed
import analysis_scripts.verify_noncombat_cross_fitted_hierarchical_learning_experiment as verifier
from analysis_scripts.noncombat_hierarchical_advantage_attribution import (
    COMPONENT_NAMES,
    FEATURE_FIELDS,
    FEATURE_SCHEMA_VERSION,
    AdvantageBatch,
    AdvantageRecord,
)
from analysis_scripts.noncombat_hierarchical_policy_objective import (
    build_hierarchical_policy_terms,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    build_transition,
)


class _TinyRanker(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(
            torch.tensor([0.3, -0.2, 0.1], dtype=torch.float32)
        )

    def scores(self) -> torch.Tensor:
        return self.weight


def _rollout_candidate(action_id: str, kind: str) -> dict[str, object]:
    return {
        "action_id": action_id,
        "available": True,
        "category": "shop",
        "kind": kind,
        "label": action_id,
        "raw": {"price": 0 if action_id == "leave" else 25},
    }


def _rollout_provenance() -> dict[str, object]:
    return {
        "adapter_commit": "1" * 40,
        "adapter_source_sha256": "2" * 64,
        "build": {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_policy_id": "test-baseline-v1",
            "compiler": "test-compiler",
            "cpp_standard": 201703,
            "native_target_policy_id": NATIVE_TARGET_POLICY_ID,
            "pybind11_version": "3.0.2",
            "python": "3.10.18",
        },
        "module_sha256": "3" * 64,
        "module_size_bytes": 123,
        "simulator_commit": "4" * 40,
        "simulator_dirty": False,
        "simulator_source_file_count": 79,
        "simulator_source_sha256": "5" * 64,
        "submodules": {"json": "6" * 40, "pybind11": "7" * 40},
    }


class _OneStepEnvironment:
    def __init__(self, seed: int, *, mutate_source: bool = False) -> None:
        self.seed = seed
        self.mutate_source = mutate_source
        self.terminal = False
        self.selected: str | None = None

    def snapshot(self) -> dict[str, object]:
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {"history": [], "policy_id": "test-control"},
            "category": None if self.terminal else "shop",
            "decision_count": 1 if self.terminal else 0,
            "schema_version": STATE_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "state": {
                "cur_hp": 80,
                "floor": 1 if self.terminal else 0,
                "gold": 100 + self.seed,
                "outcome": "player_loss" if self.terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": self.terminal,
        }

    def legal_actions(self) -> list[dict[str, object]]:
        if self.terminal:
            return []
        return [
            _rollout_candidate("leave", "leave"),
            _rollout_candidate("buy", "buy"),
        ]

    def clone(self):
        return self if self.mutate_source else copy.deepcopy(self)

    def step(self, action_id: str) -> dict[str, object]:
        before = self.snapshot()
        candidates = self.legal_actions()
        self.selected = action_id
        self.terminal = True
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=action_id,
            after=self.snapshot(),
            provenance=_rollout_provenance(),
        )


def _terms(model: _TinyRanker):
    candidates = (
        {"action_id": "take-a", "kind": "take"},
        {"action_id": "take-b", "kind": "take"},
        {"action_id": "skip", "kind": "skip"},
    )
    return (
        build_hierarchical_policy_terms(model.scores(), candidates, "take-b"),
        build_hierarchical_policy_terms(model.scores(), candidates, "skip"),
    )


def _record(
    *,
    decision_id: str,
    trajectory_id: str,
    fold_id: str,
    raw_return: float,
    prediction: float,
    fit_id: str,
) -> AdvantageRecord:
    return AdvantageRecord(
        decision_id=decision_id,
        decision_index=0,
        trajectory_id=trajectory_id,
        fold_id=fold_id,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        feature_sha256="1" * 64,
        feature_fields=FEATURE_FIELDS,
        raw_return=raw_return,
        baseline_mode="cross_fitted",
        baseline_prediction=prediction,
        baseline_fit_trajectory_ids=(fit_id,),
        baseline_fit_sha256="2" * 64,
        scale_mode="fixed_unit",
        scale=1.0,
        scale_fit_trajectory_ids=(),
        scale_fit_sha256="3" * 64,
        advantage=raw_return - prediction,
        confounding_reduction_claimed=False,
    )


def _advantage_batch() -> AdvantageBatch:
    return AdvantageBatch(
        records=(
            _record(
                decision_id="decision-0",
                trajectory_id="trajectory-0",
                fold_id="fold-0",
                raw_return=2.0,
                prediction=0.5,
                fit_id="trajectory-1",
            ),
            _record(
                decision_id="decision-1",
                trajectory_id="trajectory-1",
                fold_id="fold-1",
                raw_return=1.0,
                prediction=0.25,
                fit_id="trajectory-0",
            ),
        ),
        fold_trajectories=(
            ("fold-0", ("trajectory-0",)),
            ("fold-1", ("trajectory-1",)),
        ),
        fold_manifest_sha256="4" * 64,
    )


def _objective_fixture(categories=("card_reward", "shop")):
    model = _TinyRanker()
    terms = _terms(model)
    batch = _advantage_batch()
    objective = runtime.build_cross_fitted_objective(
        terms=terms,
        categories=categories,
        advantage_batch=batch,
    )
    return model, terms, batch, objective


def test_runtime_initialization_preserves_consumed_ranker_and_learning_controls():
    successor = runtime.initialize_training_runtime()
    predecessor = consumed.initialize_training_runtime()

    assert successor.model.architecture_metadata() == (
        predecessor.model.architecture_metadata()
    )
    for name, value in successor.model.state_dict().items():
        assert torch.equal(value, predecessor.model.state_dict()[name])
    assert successor.optimizer.param_groups[0]["lr"] == 0.001
    assert successor.optimizer.param_groups[0]["betas"] == (0.9, 0.999)
    assert successor.optimizer.param_groups[0]["eps"] == 1e-8
    assert torch.equal(
        successor.action_generator.get_state(),
        predecessor.action_generator.get_state(),
    )
    expected_rng = random.Random(0)
    assert successor.python_rng.random() == expected_rng.random()
    metadata = runtime.runtime_metadata()
    assert metadata["algorithm"] == control.experiment_contract()["algorithm"]
    assert metadata["baseline"] == control.experiment_contract()["baseline"]
    assert metadata["adapter_api_version"] == ADAPTER_API_VERSION
    assert metadata["device"] == "cpu"
    assert metadata["environment"] == control.experiment_contract()["environment"]
    assert metadata["authority"] == control.registration_authority()


def test_complete_trajectory_builds_undiscounted_bounded_return_to_go():
    features = tuple(
        torch.full((128,), float(index), dtype=torch.float32)
        for index in range(3)
    )

    decisions = runtime.build_trajectory_baseline_decisions(
        seed=17,
        trajectory_id="trajectory-17",
        decision_ids=("d0", "d1", "d2"),
        categories=("shop", "event", "card_reward"),
        state_features=features,
        rewards=(0.0, 0.0, 3.0),
    )

    assert [decision.decision_index for decision in decisions] == [0, 1, 2]
    assert [decision.raw_return for decision in decisions] == [3.0, 3.0, 3.0]
    assert all(decision.seed == 17 for decision in decisions)
    assert all(decision.trajectory_id == "trajectory-17" for decision in decisions)
    for index, decision in enumerate(decisions):
        assert torch.equal(decision.state_features, features[index])
        assert decision.state_features.data_ptr() != features[index].data_ptr()


def test_trajectory_return_outside_registered_bounds_is_rejected():
    with pytest.raises(runtime.RuntimeBlocked, match=r"\[0, 3\]"):
        runtime.build_trajectory_baseline_decisions(
            seed=0,
            trajectory_id="trajectory-0",
            decision_ids=("d0", "d1"),
            categories=("shop", "shop"),
            state_features=(
                torch.zeros(128, dtype=torch.float32),
                torch.zeros(128, dtype=torch.float32),
            ),
            rewards=(3.0, 1.0),
        )


def test_clone_only_rollout_retains_pre_action_state_terms_reward_and_hook_order():
    runtime_state = runtime.initialize_training_runtime()
    hook_calls = []
    environments = []

    def before_environment(seed: int) -> None:
        hook_calls.append(seed)

    def factory(seed: int):
        assert hook_calls == [seed]
        environment = _OneStepEnvironment(seed)
        environments.append(environment)
        return environment

    rollout = runtime.rollout_training_episode(
        runtime_state,
        environment_factory=factory,
        seed=23,
        chunk_index=0,
        before_environment=before_environment,
    )

    assert hook_calls == [23]
    assert environments[0].terminal is False
    assert rollout.seed == 23
    assert rollout.trajectory_id == "seed-23"
    assert len(rollout.decisions) == 1
    decision = rollout.decisions[0]
    assert decision.baseline_decision.state_features.shape == (128,)
    assert decision.baseline_decision.reward == pytest.approx(1.0 / 57.0)
    assert decision.baseline_decision.raw_return == pytest.approx(1.0 / 57.0)
    assert decision.terms.selected_action_id in {"leave", "buy"}
    assert decision.diagnostic["multi_family"] is True
    assert decision.diagnostic["selected_action_id"] == (
        decision.terms.selected_action_id
    )
    assert rollout.floor_progress == pytest.approx(1.0 / 57.0)
    assert rollout.terminal_victory == 0
    assert rollout.unsupported_reason is None


def test_rollout_sampling_is_replayable_and_rejects_source_mutation():
    first_runtime = runtime.initialize_training_runtime()
    second_runtime = runtime.initialize_training_runtime()

    first = runtime.rollout_training_episode(
        first_runtime,
        environment_factory=_OneStepEnvironment,
        seed=9,
        chunk_index=0,
    )
    second = runtime.rollout_training_episode(
        second_runtime,
        environment_factory=_OneStepEnvironment,
        seed=9,
        chunk_index=0,
    )

    assert first.decisions[0].terms.selected_action_id == (
        second.decisions[0].terms.selected_action_id
    )
    assert first.decisions[0].diagnostic == second.decisions[0].diagnostic
    assert torch.equal(
        first.decisions[0].baseline_decision.state_features,
        second.decisions[0].baseline_decision.state_features,
    )
    with pytest.raises(runtime.RuntimeBlocked, match="distinct branch"):
        runtime.rollout_training_episode(
            runtime.initialize_training_runtime(),
            environment_factory=lambda seed: _OneStepEnvironment(
                seed, mutate_source=True
            ),
            seed=9,
            chunk_index=0,
        )


def test_collector_runs_exactly_64_journaled_episodes_before_one_update():
    runtime_state = runtime.initialize_training_runtime()
    events = []

    def before(seed: int) -> None:
        events.append(("before", seed))

    def after(seed: int) -> None:
        assert events[-1] == ("before", seed)
        events.append(("after", seed))

    result = runtime.collect_and_update_training_chunk(
        runtime_state,
        environment_factory=_OneStepEnvironment,
        seeds=tuple(range(64)),
        chunk_index=0,
        before_environment=before,
        after_environment=after,
        deadline=100.0,
        clock=lambda: 0.0,
    )

    assert result.seeds == tuple(range(64))
    assert len(result.episodes) == 64
    assert len(result.update.decisions) == 64
    assert events == [
        item
        for seed in range(64)
        for item in (("before", seed), ("after", seed))
    ]
    assert runtime_state.optimizer_updates == 1
    assert runtime_state.completed_episodes == 64


def test_runtime_binary_payload_is_independently_decodable():
    tensor = torch.tensor([[1.25, -2.5], [0.0, 3.0]], dtype=torch.float64)

    payload = runtime.encode_float_tensor(tensor)

    assert verifier.decode_float_payload(payload) == tuple(tensor.reshape(-1))
    assert payload["shape"] == [2, 2]
    assert payload["dtype"] == "float64"


def test_runtime_checkpoint_round_trips_model_adam_rng_and_coordinates():
    runtime_state = runtime.initialize_training_runtime()
    for parameter in runtime_state.model.parameters():
        parameter.grad = torch.full_like(parameter, 0.125)
    runtime_state.optimizer.step()
    runtime_state.next_chunk_index = 1
    runtime_state.completed_episodes = 64
    runtime_state.completed_decisions = 97
    runtime_state.optimizer_updates = 1
    runtime_state.python_rng.random()
    torch.rand(3, generator=runtime_state.action_generator)

    checkpoint = runtime.encode_runtime_checkpoint(runtime_state)
    expected_python = runtime_state.python_rng.random()
    expected_torch = torch.rand(4, generator=runtime_state.action_generator)
    restored = runtime.restore_training_runtime_from_checkpoint(checkpoint)

    assert restored.next_chunk_index == 1
    assert restored.completed_episodes == 64
    assert restored.completed_decisions == 97
    assert restored.optimizer_updates == 1
    assert restored.python_rng.random() == expected_python
    assert torch.equal(
        torch.rand(4, generator=restored.action_generator), expected_torch
    )
    for name, value in runtime_state.model.state_dict().items():
        assert torch.equal(restored.model.state_dict()[name], value)
    for original, recovered in zip(
        runtime_state.model.parameters(), restored.model.parameters(), strict=True
    ):
        original_state = runtime_state.optimizer.state[original]
        recovered_state = restored.optimizer.state[recovered]
        assert int(original_state["step"].item()) == int(
            recovered_state["step"].item()
        )
        assert torch.equal(original_state["exp_avg"], recovered_state["exp_avg"])
        assert torch.equal(
            original_state["exp_avg_sq"], recovered_state["exp_avg_sq"]
        )

    changed = {**checkpoint, "checkpoint_sha256": "0" * 64}
    with pytest.raises(runtime.RuntimeBlocked, match="checkpoint"):
        runtime.restore_training_runtime_from_checkpoint(changed)


def test_family_saturation_uses_only_exact_trailing_four_chunk_window():
    chunks = []
    for chunk_index in range(4):
        chunks.append(
            {
                "chunk_index": chunk_index,
                "decisions": [
                    {
                        "category": "card_reward",
                        "diagnostic": {
                            "multi_family": True,
                            "raw_score_max_family_ids": ["take"],
                        },
                    }
                    for _ in range(16)
                ],
            }
        )

    saturated = runtime.classify_family_saturation(chunks)

    assert saturated == {
        "category": "card_reward",
        "family": "take",
        "multi_family_decisions": 64,
        "stop": True,
        "window_chunk_indices": [0, 1, 2, 3],
    }
    changed = [dict(chunk) for chunk in chunks]
    changed[-1] = {
        **changed[-1],
        "decisions": [
            *changed[-1]["decisions"][:-1],
            {
                "category": "card_reward",
                "diagnostic": {
                    "multi_family": True,
                    "raw_score_max_family_ids": ["skip"],
                },
            },
        ],
    }
    assert runtime.classify_family_saturation(changed)["stop"] is False
    assert runtime.classify_family_saturation(chunks[:3])["stop"] is False


def test_objective_uses_exact_five_components_and_global_denominator():
    model, terms, _, objective = _objective_fixture()

    assert tuple(objective.components) == COMPONENT_NAMES
    denominator = 2.0
    expected = (
        -terms[0].selected_family_log_probability * 1.5 / denominator,
        -terms[0].selected_conditional_log_probability * 1.5 / denominator,
        -terms[1].selected_joint_log_probability * 0.75 / denominator,
        -0.01
        * torch.stack([term.family_entropy for term in terms]).mean(),
        -0.01
        * torch.stack([term.conditional_entropy for term in terms]).mean(),
    )
    for actual, wanted in zip(objective.components.values(), expected, strict=True):
        assert torch.equal(actual, wanted)
    assert torch.equal(objective.full_loss, sum(expected[1:], expected[0]))
    assert torch.equal(
        objective.advantages,
        torch.tensor([1.5, 0.75], dtype=torch.float64),
    )
    assert all(value.requires_grad for value in objective.components.values())
    assert model.weight.grad is None


def test_empty_policy_subset_remains_graph_connected_zero():
    model, _, _, objective = _objective_fixture(
        categories=("card_reward", "card_reward")
    )

    empty = objective.components["other_policy"]
    gradient = torch.autograd.grad(empty, model.weight, retain_graph=True)[0]
    assert empty.item() == 0.0
    assert empty.requires_grad
    assert torch.equal(gradient, torch.zeros_like(model.weight))


def test_objective_rejects_post_advantage_transformation():
    model = _TinyRanker()
    terms = _terms(model)
    batch = _advantage_batch()
    changed = replace(
        batch,
        records=(replace(batch.records[0], advantage=0.0), batch.records[1]),
    )

    with pytest.raises(runtime.RuntimeBlocked, match="advantage"):
        runtime.build_cross_fitted_objective(
            terms=terms,
            categories=("card_reward", "shop"),
            advantage_batch=changed,
        )


def test_gradient_evidence_reconstructs_and_retains_both_clip_paths():
    model, terms, batch, objective = _objective_fixture()

    evidence = runtime.build_gradient_update_evidence(
        objective=objective,
        terms=terms,
        raw_returns=[record.raw_return for record in batch.records],
        named_parameters=tuple(model.named_parameters()),
    )

    assert evidence.ledger.component_names == COMPONENT_NAMES
    assert evidence.installed_gradient.dtype == torch.float32
    assert evidence.installed_gradient.device.type == "cpu"
    assert torch.equal(
        evidence.installed_gradient,
        evidence.ledger.clipped_full_gradient.to(dtype=torch.float32),
    )
    assert evidence.consumed_torch_clipped_gradient.shape == (
        model.weight.numel(),
    )
    assert evidence.legacy_gradient.shape == (model.weight.numel(),)
    assert torch.equal(
        evidence.legacy_normalized_returns,
        consumed.normalize_returns([2.0, 1.0]),
    )
    assert evidence.gradient_comparison["difference_norm"] >= 0.0
    assert evidence.clip_comparison["max_abs_difference"] >= 0.0
    assert model.weight.grad is None


@pytest.mark.parametrize(
    "returns",
    ([1.0, 1.0], [0.0, 2e-12], [0.0, 4e-12]),
)
def test_legacy_diagnostic_calls_consumed_threshold_behavior(returns):
    model = _TinyRanker()
    terms = _terms(model)

    diagnostic = runtime.build_legacy_objective_diagnostic(
        terms=terms,
        raw_returns=returns,
        named_parameters=tuple(model.named_parameters()),
    )

    assert torch.equal(
        diagnostic.normalized_returns,
        consumed.normalize_returns(returns),
    )


def test_validated_gradient_is_installed_before_one_exact_adam_step():
    model, terms, batch, objective = _objective_fixture()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=0.001,
        betas=(0.9, 0.999),
        eps=1e-8,
        weight_decay=0.0,
        amsgrad=False,
    )
    evidence = runtime.build_gradient_update_evidence(
        objective=objective,
        terms=terms,
        raw_returns=[record.raw_return for record in batch.records],
        named_parameters=tuple(model.named_parameters()),
    )
    before = model.weight.detach().clone()

    step = runtime.apply_validated_adam_step(
        optimizer=optimizer,
        named_parameters=tuple(model.named_parameters()),
        evidence=evidence,
    )

    assert step.pre_steps == (0,)
    assert step.post_steps == (1,)
    assert torch.equal(step.installed_gradient, evidence.installed_gradient)
    assert not torch.equal(model.weight.detach(), before)
    assert torch.equal(
        model.weight.grad.reshape(-1), evidence.installed_gradient
    )
    assert torch.isfinite(step.post_parameters[0]).all().item()
    assert torch.isfinite(step.post_exp_avg[0]).all().item()
    assert torch.isfinite(step.post_exp_avg_sq[0]).all().item()
    replayed = verifier.replay_adam_transition(
        pre_parameters=step.pre_parameters[0].reshape(-1).tolist(),
        installed_gradient=step.installed_gradient.tolist(),
        pre_exp_avg=step.pre_exp_avg[0].reshape(-1).tolist(),
        pre_exp_avg_sq=step.pre_exp_avg_sq[0].reshape(-1).tolist(),
        pre_step=step.pre_steps[0],
        post_parameters=step.post_parameters[0].reshape(-1).tolist(),
        post_exp_avg=step.post_exp_avg[0].reshape(-1).tolist(),
        post_exp_avg_sq=step.post_exp_avg_sq[0].reshape(-1).tolist(),
        post_step=step.post_steps[0],
    )
    assert replayed["post_step"] == 1


def test_parameter_drift_blocks_gradient_installation_without_step():
    model, terms, batch, objective = _objective_fixture()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    evidence = runtime.build_gradient_update_evidence(
        objective=objective,
        terms=terms,
        raw_returns=[record.raw_return for record in batch.records],
        named_parameters=tuple(model.named_parameters()),
    )
    with torch.no_grad():
        model.weight.add_(1.0)

    with pytest.raises(runtime.RuntimeBlocked, match="parameter drift"):
        runtime.apply_validated_adam_step(
            optimizer=optimizer,
            named_parameters=tuple(model.named_parameters()),
            evidence=evidence,
        )
    assert optimizer.state == {}


def test_optimizer_control_drift_blocks_before_step():
    model, terms, batch, objective = _objective_fixture()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    evidence = runtime.build_gradient_update_evidence(
        objective=objective,
        terms=terms,
        raw_returns=[record.raw_return for record in batch.records],
        named_parameters=tuple(model.named_parameters()),
    )

    with pytest.raises(runtime.RuntimeBlocked, match="Adam"):
        runtime.apply_validated_adam_step(
            optimizer=optimizer,
            named_parameters=tuple(model.named_parameters()),
            evidence=evidence,
        )
    assert optimizer.state == {}


def _synthetic_chunk(runtime_state):
    candidates = (
        {"action_id": "take", "kind": "take"},
        {"action_id": "skip", "kind": "skip"},
    )
    scores = runtime_state.model(
        torch.zeros(1024, dtype=torch.float32),
        torch.stack(
            (
                torch.zeros(1024, dtype=torch.float32),
                torch.ones(1024, dtype=torch.float32),
            )
        ),
    )
    terms = build_hierarchical_policy_terms(scores, candidates, "take")
    traces = []
    for seed in range(64):
        traces.append(
            runtime.CrossFittedTrainingDecision(
                baseline_decision=runtime.BaselineDecision(
                    category="card_reward" if seed % 2 == 0 else "shop",
                    decision_id=f"seed-{seed}:decision-0",
                    decision_index=0,
                    raw_return=1.0,
                    seed=seed,
                    state_features=torch.zeros(128, dtype=torch.float32),
                    trajectory_id=f"seed-{seed}",
                ),
                terms=terms,
            )
        )
    return tuple(traces)


def test_one_cross_fitted_chunk_updates_once_after_complete_evidence():
    runtime_state = runtime.initialize_training_runtime()
    traces = _synthetic_chunk(runtime_state)
    before = {
        name: value.detach().clone()
        for name, value in runtime_state.model.named_parameters()
    }

    result = runtime.run_cross_fitted_chunk_update(
        runtime_state,
        chunk_index=0,
        decisions=traces,
    )

    assert result.chunk_index == 0
    assert len(result.baseline.advantage_batch.records) == 64
    assert result.gradient.ledger.component_names == COMPONENT_NAMES
    assert result.adam.post_steps == tuple(
        1 for _ in runtime_state.model.parameters()
    )
    assert runtime_state.next_chunk_index == 1
    assert runtime_state.completed_episodes == 64
    assert runtime_state.completed_decisions == 64
    assert runtime_state.optimizer_updates == 1
    assert any(
        not torch.equal(value.detach(), before[name])
        for name, value in runtime_state.model.named_parameters()
    )


def test_chunk_coordinate_and_exact_trajectory_count_fail_before_step():
    runtime_state = runtime.initialize_training_runtime()
    traces = _synthetic_chunk(runtime_state)

    with pytest.raises(runtime.RuntimeBlocked, match="chunk"):
        runtime.run_cross_fitted_chunk_update(
            runtime_state,
            chunk_index=1,
            decisions=traces,
        )
    with pytest.raises(runtime.RuntimeBlocked, match="64"):
        runtime.run_cross_fitted_chunk_update(
            runtime_state,
            chunk_index=0,
            decisions=traces[:-1],
        )
    assert runtime_state.optimizer_updates == 0
    assert runtime_state.optimizer.state == {}


def test_chunk_evidence_is_deterministic_and_independently_replayable():
    model = _TinyRanker()
    reusable_terms = _terms(model)
    traces = []
    for seed in range(64):
        traces.append(
            runtime.CrossFittedTrainingDecision(
                baseline_decision=runtime.BaselineDecision(
                    category="card_reward" if seed % 2 == 0 else "shop",
                    decision_id=f"seed-{seed}:decision-0",
                    decision_index=0,
                    raw_return=float(seed % 4),
                    seed=seed,
                    state_features=torch.zeros(128, dtype=torch.float32),
                    trajectory_id=f"seed-{seed}",
                    reward=float(seed % 4),
                ),
                terms=reusable_terms[seed % 2],
                diagnostic={
                    "candidate_scores": {
                        "skip": 0.1,
                        "take-a": 0.3,
                        "take-b": -0.2,
                    },
                    "candidates": [
                        {"action_id": "take-a", "kind": "take"},
                        {"action_id": "take-b", "kind": "take"},
                        {"action_id": "skip", "kind": "skip"},
                    ],
                    "category": "card_reward" if seed % 2 == 0 else "shop",
                    "conditional_probabilities": {
                        "skip": 1.0,
                        "take-a": 0.5,
                        "take-b": 0.5,
                    },
                    "family_order": ["skip", "take"],
                    "family_probabilities": {"skip": 0.5, "take": 0.5},
                    "joint_probabilities": {
                        "skip": 0.5,
                        "take-a": 0.25,
                        "take-b": 0.25,
                    },
                    "multi_family": True,
                    "raw_score_max_action_ids": ["take-a"],
                    "raw_score_max_family_ids": ["take"],
                    "selected_action_id": reusable_terms[
                        seed % 2
                    ].selected_action_id,
                    "selected_family": reusable_terms[seed % 2].selected_family,
                    "selection_mode": "synthetic-source-test",
                },
            )
        )
    baseline = runtime.build_cross_fitted_baseline(
        tuple(trace.baseline_decision for trace in traces)
    )
    by_id = {trace.baseline_decision.decision_id: trace for trace in traces}
    ordered = tuple(
        by_id[record.decision_id] for record in baseline.advantage_batch.records
    )
    terms = tuple(trace.terms for trace in ordered)
    objective = runtime.build_cross_fitted_objective(
        terms=terms,
        categories=tuple(trace.baseline_decision.category for trace in ordered),
        advantage_batch=baseline.advantage_batch,
    )
    gradient = runtime.build_gradient_update_evidence(
        objective=objective,
        terms=terms,
        raw_returns=tuple(
            record.raw_return for record in baseline.advantage_batch.records
        ),
        named_parameters=tuple(model.named_parameters()),
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    adam = runtime.apply_validated_adam_step(
        optimizer=optimizer,
        named_parameters=tuple(model.named_parameters()),
        evidence=gradient,
    )
    update = runtime.CrossFittedChunkUpdate(
        chunk_index=0,
        baseline=baseline,
        objective=objective,
        gradient=gradient,
        adam=adam,
        decisions=ordered,
    )

    first = runtime.build_chunk_evidence(update)
    second = runtime.build_chunk_evidence(update)

    assert first == second
    content = {key: value for key, value in first.items() if key != "content_sha256"}
    canonical = verifier.canonical_json_bytes(content)
    assert first["content_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert verifier.decode_float_payload(first["gradients"]["full"]) == tuple(
        gradient.ledger.full_gradient
    )
    parameter = first["adam"]["parameters"][0]
    replayed = verifier.replay_adam_transition(
        pre_parameters=verifier.decode_float_payload(parameter["pre_parameter"]),
        installed_gradient=verifier.decode_float_payload(
            parameter["installed_gradient"]
        ),
        pre_exp_avg=verifier.decode_float_payload(parameter["pre_exp_avg"]),
        pre_exp_avg_sq=verifier.decode_float_payload(parameter["pre_exp_avg_sq"]),
        pre_step=parameter["pre_step"],
        post_parameters=verifier.decode_float_payload(parameter["post_parameter"]),
        post_exp_avg=verifier.decode_float_payload(parameter["post_exp_avg"]),
        post_exp_avg_sq=verifier.decode_float_payload(parameter["post_exp_avg_sq"]),
        post_step=parameter["post_step"],
    )
    assert replayed["post_step"] == 1
    stored_first, binding_first = verifier.encode_deterministic_gzip(canonical)
    stored_second, binding_second = verifier.encode_deterministic_gzip(canonical)
    assert stored_first == stored_second
    assert binding_first == binding_second
    assert verifier.verify_deterministic_gzip(
        stored_first, binding_first
    ) == canonical
