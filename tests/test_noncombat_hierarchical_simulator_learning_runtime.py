from __future__ import annotations

import copy
import hashlib
import math

import pytest
import torch

from analysis_scripts import noncombat_hierarchical_simulator_learning_experiment as control
from analysis_scripts import noncombat_hierarchical_simulator_learning_runtime as runtime
from analysis_scripts import verify_noncombat_hierarchical_simulator_learning_experiment as verifier
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    TARGET_CATEGORIES,
    build_transition,
)


def _candidate(
    action_id: str,
    category: str,
    *,
    kind: str,
    price: int,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "available": True,
        "category": category,
        "kind": kind,
        "label": action_id,
        "raw": {"price": price},
    }


def _provenance() -> dict[str, object]:
    return {
        "adapter_commit": "1" * 40,
        "adapter_source_sha256": "2" * 64,
        "build": {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_policy_id": "sts_lightspeed_simple_agent_no_potions_v1",
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


class OneStepEnvironment:
    def __init__(
        self,
        seed: int,
        *,
        mutate_source: bool = False,
        nonfinite: bool = False,
    ) -> None:
        self.seed = seed
        self.mutate_source = mutate_source
        self.nonfinite = nonfinite
        self.selected: str | None = None
        self.terminal = False

    @property
    def category(self) -> str:
        return TARGET_CATEGORIES[self.seed % len(TARGET_CATEGORIES)]

    def snapshot(self) -> dict[str, object]:
        terminal_floor = 57 if self.selected == "good" else 3
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {"history": [], "policy_id": "test-control"},
            "category": None if self.terminal else self.category,
            "decision_count": 1 if self.terminal else 0,
            "schema_version": STATE_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "state": {
                "cur_hp": 80,
                "floor": terminal_floor if self.terminal else 0,
                "gold": math.inf if self.nonfinite else 99 + self.seed,
                "outcome": (
                    "player_victory"
                    if self.terminal and self.selected == "good"
                    else "player_loss" if self.terminal else "undecided"
                ),
                "seed": str(self.seed),
            },
            "terminal": self.terminal,
        }

    def legal_actions(self) -> list[dict[str, object]]:
        if self.terminal:
            return []
        kinds = {
            "card_reward": ("skip", "take"),
            "event": ("choose", "choose"),
            "route": ("choose", "choose"),
            "shop": ("leave", "buy"),
        }[self.category]
        return [
            _candidate("bad", self.category, kind=kinds[0], price=0),
            _candidate("good", self.category, kind=kinds[1], price=1),
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
            provenance=_provenance(),
        )


class UnsupportedOneStepEnvironment(OneStepEnvironment):
    def step(self, action_id: str) -> dict[str, object]:
        raise RuntimeError("unsupported_shop_courier_restock_semantics")


def _factory(seed: int) -> OneStepEnvironment:
    return OneStepEnvironment(seed)


def _model_bytes(model: torch.nn.Module) -> bytes:
    return runtime.simulator_adapter.canonical_json_bytes(
        runtime.encode_model_state(model)
    )


def _simple_candidates(*kinds: str) -> list[dict[str, str]]:
    return [
        {"action_id": f"action-{index}", "kind": kind}
        for index, kind in enumerate(kinds)
    ]


def _gate_row(
    category: str,
    index: int,
    *,
    selected_family: str,
    alternative_family: str,
) -> dict[str, object]:
    selected_action = f"{category}:{selected_family}:{index}"
    alternative_action = f"{category}:{alternative_family}:{index}:alt"
    families = [selected_family, alternative_family]
    return {
        "candidates": [
            {"action_id": selected_action, "kind": selected_family},
            {"action_id": alternative_action, "kind": alternative_family},
        ],
        "category": category,
        "legal_action_ids": [selected_action, alternative_action],
        "multi_family": len(set(families)) > 1,
        "raw_score_max_family_ids": [selected_family],
        "selected_action_id": selected_action,
        "selected_family": selected_family,
        "state_effect": {
            "max_abs_relative_score_change": 0.25,
            "relative_order_changed": True,
        },
    }


def _passing_evaluation(cohort: str = "canary") -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for category, families in (
        ("card_reward", ("take", "skip")),
        ("shop", ("buy", "leave")),
    ):
        for index in range(32):
            selected = families[index % 2]
            alternative = families[(index + 1) % 2]
            rows.append(
                _gate_row(
                    category,
                    index,
                    selected_family=selected,
                    alternative_family=alternative,
                )
            )
    for category in ("event", "route"):
        for index in range(4):
            rows.append(
                _gate_row(
                    category,
                    index,
                    selected_family="choose",
                    alternative_family="choose",
                )
            )
    policy = {
        "categories": list(TARGET_CATEGORIES),
        "diagnostic_rows": rows,
        "replay_exact": True,
        "unsupported_episodes": 0,
        "victories": 0,
    }
    return {
        "cohort": cohort,
        "evaluation_episodes": 4,
        "floor_difference_ci": {
            "confidence": 0.95,
            "lower": 1.0,
            "mean": 1.0,
            "resamples": 10_000,
            "seed": 0,
            "upper": 1.0,
        },
        "initial": copy.deepcopy(policy),
        "paired_rows": [{"floor_difference": 1.0, "seed": 1}],
        "trained": copy.deepcopy(policy),
        "unsupported_rate": 0.0,
        "unsupported_rate_denominator": 2,
    }


def test_runtime_metadata_matches_the_control_contract_and_is_all_false():
    metadata = runtime.runtime_metadata()
    contract = control.experiment_contract()

    assert metadata["algorithm"] == contract["algorithm"]
    assert metadata["adapter_api_version"] == ADAPTER_API_VERSION
    assert metadata["device"] == contract["identity"]["device"]
    assert metadata["evaluation_selection"] == contract["evaluation"]["selection"]
    assert set(metadata["authority"].values()) == {False}


def test_evaluation_resource_charges_are_atomic_and_bounded():
    state = runtime.initialize_training_runtime()

    resources = runtime.record_evaluation_resources(
        state, episodes=512, charged_seconds=1.5
    )

    assert resources == {
        "charged_seconds": 1.5,
        "evaluation_episodes": 512,
        "optimizer_updates": 0,
        "total_episodes": 512,
        "training_episodes": 0,
    }
    before = copy.deepcopy(resources)
    with pytest.raises(runtime.RuntimeBlocked, match="evaluation episode"):
        runtime.record_evaluation_resources(
            state, episodes=2_049, charged_seconds=1.0
        )
    assert runtime.runtime_resource_use(state) == before

    restored = runtime.initialize_training_runtime()
    assert runtime.restore_consumed_resource_prefix(restored, before) == before
    changed = copy.deepcopy(before)
    changed["training_episodes"] = 1
    changed["total_episodes"] = 513
    assert runtime.restore_consumed_resource_prefix(restored, changed) == changed

    regressed = copy.deepcopy(changed)
    regressed["training_episodes"] = 0
    regressed["total_episodes"] = 512
    with pytest.raises(runtime.RuntimeBlocked, match="monotonic"):
        runtime.restore_consumed_resource_prefix(restored, regressed)


def test_sampling_calls_family_then_conditional_even_for_one_candidate(monkeypatch):
    calls: list[tuple[int, ...]] = []
    original = torch.multinomial

    def recording_multinomial(input_tensor, *args, **kwargs):
        calls.append(tuple(input_tensor.shape))
        return original(input_tensor, *args, **kwargs)

    monkeypatch.setattr(torch, "multinomial", recording_multinomial)
    generator = torch.Generator(device="cpu").manual_seed(7)

    sample = runtime.sample_hierarchical_action(
        torch.tensor([0.0], dtype=torch.float32),
        _simple_candidates("choose"),
        generator,
    )

    assert calls == [(1,), (1,)]
    assert sample.selected_action_id == "action-0"
    assert sample.selected_family == "choose"
    assert sample.generator_state_before_sha256 == runtime.torch_generator_state_sha256(
        torch.Generator(device="cpu").manual_seed(7)
    )


def test_hierarchical_sampling_is_exactly_replayable_and_identity_aligned():
    scores = torch.tensor([2.0, 0.0, 1.0], dtype=torch.float32)
    candidates = _simple_candidates("take", "take", "skip")
    first_generator = torch.Generator(device="cpu").manual_seed(19)
    second_generator = torch.Generator(device="cpu").manual_seed(19)

    first = runtime.sample_hierarchical_action(scores, candidates, first_generator)
    second = runtime.sample_hierarchical_action(scores, candidates, second_generator)

    assert first.selected_action_id == second.selected_action_id
    assert first.selected_family == second.selected_family
    assert first.selected_candidate_index == second.selected_candidate_index
    assert first.generator_state_after_family_sha256 == (
        second.generator_state_after_family_sha256
    )
    assert first.generator_state_after_conditional_sha256 == (
        second.generator_state_after_conditional_sha256
    )
    assert first.terms.selected_action_id == first.selected_action_id
    assert first.terms.selected_family == first.selected_family


def test_reinforce_loss_uses_joint_log_probability_and_only_two_entropy_terms():
    first_scores = torch.tensor(
        [2.0, 0.0, 1.0], dtype=torch.float32, requires_grad=True
    )
    second_scores = torch.tensor(
        [0.5, 1.5, -0.5], dtype=torch.float32, requires_grad=True
    )
    candidates = _simple_candidates("take", "take", "skip")
    terms = [
        runtime.hierarchical_objective.build_hierarchical_policy_terms(
            first_scores, candidates, "action-1"
        ),
        runtime.hierarchical_objective.build_hierarchical_policy_terms(
            second_scores, candidates, "action-2"
        ),
    ]
    returns = torch.tensor([1.0, -1.0], dtype=torch.float64)

    result = runtime.build_reinforce_loss(terms, returns)
    expected_policy = -torch.stack(
        [term.selected_joint_log_probability for term in terms]
    ).mul(returns).mean()
    expected = (
        expected_policy
        - 0.01 * torch.stack([term.family_entropy for term in terms]).mean()
        - 0.01 * torch.stack([term.conditional_entropy for term in terms]).mean()
    )

    assert torch.equal(result.policy_loss, expected_policy)
    assert torch.equal(result.loss, expected)
    result.loss.backward()
    assert first_scores.grad is not None and torch.isfinite(first_scores.grad).all()
    assert second_scores.grad is not None and torch.isfinite(second_scores.grad).all()


def test_return_normalization_preserves_the_frozen_float32_epsilon_boundary():
    near_constant = runtime.normalize_returns(
        torch.tensor([0.0, 1e-13], dtype=torch.float32)
    )
    ordinary = torch.tensor([1.0, 2.0], dtype=torch.float32)
    expected = (ordinary - ordinary.mean()) / (
        ordinary.std(unbiased=False) + 1e-8
    )

    assert near_constant.dtype == torch.float32
    assert torch.equal(near_constant, torch.zeros_like(near_constant))
    assert torch.equal(runtime.normalize_returns(ordinary), expected)


def test_raw_score_selection_fails_closed_with_the_complete_tie_set():
    candidates = _simple_candidates("take", "skip", "take")

    with pytest.raises(runtime.RawScoreTieError) as caught:
        runtime.select_unique_raw_score_action(
            torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32), candidates
        )

    assert caught.value.action_ids == ("action-0", "action-1")


def test_rollout_uses_a_clone_formal_reward_and_preserves_the_source():
    source = OneStepEnvironment(3)
    before_snapshot = copy.deepcopy(source.snapshot())
    before_candidates = copy.deepcopy(source.legal_actions())
    model = runtime.initialize_training_runtime().model

    rollout = runtime.rollout_episode(
        model,
        environment_factory=lambda seed: source,
        seed=3,
        training=False,
        action_generator=None,
    )

    assert rollout.decision_count == 1
    assert rollout.formal_return == sum(rollout.rewards)
    assert set(rollout.diagnostic_rows[0]["formal_reward"]) == {
        "floor_progress",
        "scalar_reward",
        "terminal_victory",
    }
    assert source.snapshot() == before_snapshot
    assert source.legal_actions() == before_candidates


def test_independent_verifier_recomputes_runtime_generated_diagnostics():
    state = runtime.initialize_training_runtime()
    training = runtime.rollout_episode(
        state.model,
        environment_factory=_factory,
        seed=0,
        training=True,
        action_generator=state.action_generator,
        chunk_index=0,
    )
    evaluation = runtime.rollout_episode(
        state.model,
        environment_factory=_factory,
        seed=1,
        training=False,
        action_generator=None,
    )

    assert verifier._validate_diagnostic_row(
        training.diagnostic_rows[0],
        training=True,
        expected_chunk=0,
        label="runtime training diagnostic",
    ) == training.diagnostic_rows[0]
    assert verifier._validate_diagnostic_row(
        evaluation.diagnostic_rows[0],
        training=False,
        expected_chunk=None,
        label="runtime evaluation diagnostic",
    ) == evaluation.diagnostic_rows[0]


def test_registered_unsupported_episode_is_retained_and_measured():
    model = runtime.initialize_training_runtime().model

    rollout = runtime.rollout_episode(
        model,
        environment_factory=lambda seed: UnsupportedOneStepEnvironment(seed),
        seed=3,
        training=False,
        action_generator=None,
        deadline=60.0,
        clock=lambda: 0.0,
    )
    paired = runtime.paired_policy_evaluation(
        model,
        model,
        environment_factory=lambda seed: UnsupportedOneStepEnvironment(seed),
        seeds=(3,),
        cohort="canary",
        deadline=60.0,
        clock=lambda: 0.0,
    )

    assert rollout.decision_count == 1
    assert rollout.rewards == (0.0,)
    assert rollout.unsupported_reason == "unsupported_shop_courier_restock_semantics"
    assert rollout.final_snapshot["terminal"] is False
    assert paired["initial"]["unsupported_episodes"] == 1
    assert paired["trained"]["unsupported_episodes"] == 1
    assert paired["unsupported_rate"] == 1.0


def test_evaluation_default_deadline_is_bounded_before_environment_construction():
    touched: list[int] = []
    readings = iter((0.0, runtime.MAX_WALL_SECONDS + 1.0))

    with pytest.raises(runtime.RuntimeBlocked, match="wall-time"):
        runtime.evaluate_frozen_policy(
            runtime.initialize_training_runtime().model,
            environment_factory=lambda seed: touched.append(seed),
            seeds=(1,),
            cohort="canary",
            deadline=None,
            clock=lambda: next(readings),
        )

    assert touched == []


def test_resolved_default_deadline_accepts_exact_ceiling_at_nonzero_clock():
    now = 245_428.437
    deadline = runtime._resolve_deadline(None, lambda: now, label="outer")

    assert runtime._resolve_deadline(deadline, lambda: now, label="nested") == deadline
    with pytest.raises(runtime.RuntimeBlocked, match="exceeds"):
        runtime._resolve_deadline(deadline + 1.0, lambda: now, label="nested")


def test_failed_training_chunk_rolls_back_model_optimizer_generator_and_coordinates():
    state = runtime.initialize_training_runtime()
    model_before = _model_bytes(state.model)
    optimizer_before = runtime.encode_optimizer_state(state.optimizer)
    generator_before = state.action_generator.get_state().clone()

    with pytest.raises(runtime.RuntimeBlocked, match="finite"):
        runtime.run_training_chunk(
            state,
            environment_factory=lambda seed: OneStepEnvironment(
                seed, nonfinite=True
            ),
            seeds=tuple(range(runtime.EPISODES_PER_UPDATE)),
            chunk_index=0,
            max_wall_seconds=60.0,
        )

    assert _model_bytes(state.model) == model_before
    assert runtime.encode_optimizer_state(state.optimizer) == optimizer_before
    assert torch.equal(state.action_generator.get_state(), generator_before)
    assert state.next_chunk_index == 0
    assert state.completed_episodes == 0
    assert state.completed_decisions == 0
    assert state.optimizer_updates == 0
    assert state.training_episodes == 1


def test_post_update_failure_rolls_back_core_but_preserves_consumed_resources(
    monkeypatch,
):
    state = runtime.initialize_training_runtime()
    model_before = _model_bytes(state.model)
    optimizer_before = runtime.encode_optimizer_state(state.optimizer)
    generator_before = state.action_generator.get_state().clone()
    original = runtime._validate_runtime

    def fail_after_update(value):
        if value.optimizer_updates == 1:
            raise runtime.RuntimeBlocked("synthetic post-update validation")
        return original(value)

    monkeypatch.setattr(runtime, "_validate_runtime", fail_after_update)

    with pytest.raises(runtime.RuntimeBlocked, match="post-update"):
        runtime.run_training_chunk(
            state,
            environment_factory=_factory,
            seeds=tuple(range(runtime.EPISODES_PER_UPDATE)),
            chunk_index=0,
            max_wall_seconds=60.0,
            clock=lambda: 0.0,
        )

    assert _model_bytes(state.model) == model_before
    assert runtime.encode_optimizer_state(state.optimizer) == optimizer_before
    assert torch.equal(state.action_generator.get_state(), generator_before)
    assert state.next_chunk_index == 0
    assert state.completed_episodes == 0
    assert state.completed_decisions == 0
    assert state.optimizer_updates == 0
    assert state.training_episodes == runtime.EPISODES_PER_UPDATE


def test_episode_resource_is_debited_before_environment_access():
    state = runtime.initialize_training_runtime()
    touched: list[int] = []
    events: list[tuple[dict[str, object], dict[str, object]]] = []

    def reject_first_debit(resources, event):
        events.append((copy.deepcopy(resources), copy.deepcopy(event)))
        raise RuntimeError("synthetic ledger failure")

    with pytest.raises(runtime.RuntimeBlocked, match="ledger failure"):
        runtime.run_training_chunk(
            state,
            environment_factory=lambda seed: touched.append(seed),
            seeds=tuple(range(runtime.EPISODES_PER_UPDATE)),
            chunk_index=0,
            max_wall_seconds=60.0,
            clock=lambda: 0.0,
            on_resource_change=reject_first_debit,
        )

    assert touched == []
    assert state.training_episodes == 1
    assert events == [
        (
            {
                "charged_seconds": 0.0,
                "evaluation_episodes": 0,
                "optimizer_updates": 0,
                "total_episodes": 1,
                "training_episodes": 1,
            },
            {"kind": "episode_debited", "phase": "training", "seed": 0},
        )
    ]


def test_failed_evaluation_preserves_every_attempted_episode_debit():
    state = runtime.initialize_training_runtime()
    touched: list[int] = []

    def factory(seed):
        touched.append(seed)
        if seed == 2:
            raise RuntimeError("synthetic environment failure")
        return OneStepEnvironment(seed)

    with pytest.raises(runtime.RuntimeBlocked, match="environment construction"):
        runtime.evaluate_frozen_policy(
            state.model,
            environment_factory=factory,
            seeds=(1, 2, 3),
            cohort="canary",
            deadline=60.0,
            clock=lambda: 0.0,
            resource_runtime=state,
        )

    assert touched == [1, 2]
    assert state.evaluation_episodes == 2


def test_initial_checkpoint_is_a_strict_zero_coordinate_bootstrap():
    state = runtime.initialize_training_runtime()
    checkpoint = runtime.encode_checkpoint_state(state)
    digest = hashlib.sha256(control.canonical_json_bytes(checkpoint)).hexdigest()

    assert digest == control.INITIAL_RUNTIME_SHA256
    assert digest == verifier.INITIAL_RUNTIME_SHA256
    assert verifier._validate_runtime_checkpoint(
        checkpoint,
        0,
        strict_model_state=True,
    ) == checkpoint
    restored = runtime.restore_training_runtime_from_checkpoint(checkpoint)
    assert runtime.encode_checkpoint_state(restored) == checkpoint


def test_independent_objective_recomputation_uses_float32_epsilon_branch():
    rows = [
        {
            "decision_index": 0,
            "entropies": {"expected_conditional": 0.0, "family": 0.0},
            "formal_reward": {"scalar_reward": reward},
            "seed": seed,
            "selected_terms": {"joint_log_probability": log_probability},
        }
        for seed, reward, log_probability in (
            (1, 1.0, -1.0),
            (2, 1.0 + 2e-12, -2.0),
        )
    ]

    normalized = runtime.normalize_returns([1.0, 1.0 + 2e-12])
    recomputed = verifier._recompute_training_objective(rows, [1, 2])

    assert torch.equal(normalized, torch.zeros_like(normalized))
    assert recomputed["normalized_return_mean"] == 0.0
    assert recomputed["normalized_return_std"] == 0.0
    assert recomputed["policy_loss"] == 0.0


def test_independent_float32_reduction_matches_registered_torch_mean():
    values = [
        -0.15160924196243286,
        -0.12343040108680725,
        -0.07578526437282562,
        -0.20351681113243103,
        -0.06522375345230103,
    ]

    expected = float(torch.tensor(values, dtype=torch.float32).mean().item())

    assert verifier._float32_mean(values) == expected


def test_checkpoint_round_trip_restores_every_runtime_state():
    state = runtime.initialize_training_runtime()
    first_summary = runtime.run_training_chunk(
        state,
        environment_factory=_factory,
        seeds=tuple(range(runtime.EPISODES_PER_UPDATE)),
        chunk_index=0,
        max_wall_seconds=60.0,
        clock=lambda: 0.0,
    )
    assert verifier._validate_chunk(
        first_summary,
        0,
        None,
        expected_seeds=tuple(range(runtime.EPISODES_PER_UPDATE)),
    )[0] == first_summary
    checkpoint = runtime.encode_checkpoint_state(state)

    assert verifier._validate_runtime_checkpoint(
        checkpoint,
        1,
        strict_model_state=True,
    ) == checkpoint

    restored = runtime.restore_training_runtime_from_checkpoint(checkpoint)

    assert runtime.encode_checkpoint_state(restored) == checkpoint
    assert _model_bytes(restored.model) == _model_bytes(state.model)
    assert runtime.encode_optimizer_state(restored.optimizer) == (
        runtime.encode_optimizer_state(state.optimizer)
    )
    assert torch.equal(
        restored.action_generator.get_state(), state.action_generator.get_state()
    )

    continuation_seeds = tuple(
        range(runtime.EPISODES_PER_UPDATE, 2 * runtime.EPISODES_PER_UPDATE)
    )
    uninterrupted = runtime.run_training_chunk(
        state,
        environment_factory=_factory,
        seeds=continuation_seeds,
        chunk_index=1,
        max_wall_seconds=60.0,
        clock=lambda: 0.0,
    )
    resumed = runtime.run_training_chunk(
        restored,
        environment_factory=_factory,
        seeds=continuation_seeds,
        chunk_index=1,
        max_wall_seconds=60.0,
        clock=lambda: 0.0,
    )

    assert runtime.simulator_adapter.canonical_json_bytes(uninterrupted) == (
        runtime.simulator_adapter.canonical_json_bytes(resumed)
    )
    assert runtime.encode_checkpoint_state(state) == runtime.encode_checkpoint_state(
        restored
    )


def test_checkpoint_rejects_entropy_coefficient_drift():
    checkpoint = runtime.encode_checkpoint_state(runtime.initialize_training_runtime())
    checkpoint["algorithm"]["family_entropy_coefficient"] = 0.02

    with pytest.raises(runtime.RuntimeBlocked, match="coefficient"):
        runtime.restore_training_runtime_from_checkpoint(checkpoint)


def test_runtime_and_checkpoint_reject_adam_semantic_drift():
    state = runtime.initialize_training_runtime()
    state.optimizer.param_groups[0]["maximize"] = True
    with pytest.raises(runtime.RuntimeBlocked, match="maximize"):
        runtime._validate_runtime(state)

    checkpoint = runtime.encode_checkpoint_state(
        runtime.initialize_training_runtime()
    )
    optimizer = runtime.decode_optimizer_state(checkpoint["states"]["optimizer"])
    optimizer["param_groups"][0]["maximize"] = True
    checkpoint["states"]["optimizer"] = runtime._encode_state_value(optimizer)
    with pytest.raises(runtime.RuntimeBlocked, match="maximize"):
        runtime.restore_training_runtime_from_checkpoint(checkpoint)


def test_training_chunk_rejects_every_incomplete_batch_before_rng_use():
    state = runtime.initialize_training_runtime()
    generator_before = state.action_generator.get_state().clone()

    with pytest.raises(runtime.RuntimeBlocked, match="exactly"):
        runtime.run_training_chunk(
            state,
            environment_factory=_factory,
            seeds=tuple(range(runtime.EPISODES_PER_UPDATE - 1)),
            chunk_index=0,
            max_wall_seconds=60.0,
            clock=lambda: 0.0,
        )

    assert torch.equal(state.action_generator.get_state(), generator_before)


def _chunk(index: int, rows: list[dict[str, object]]) -> dict[str, object]:
    return {"chunk_index": index, "complete": True, "diagnostic_rows": rows}


def test_family_saturation_requires_four_exact_chunks_and_sixty_four_singletons():
    summaries = [
        _chunk(
            chunk_index,
            [
                {
                    "category": "card_reward",
                    "multi_family": True,
                    "raw_score_max_family_ids": ["take"],
                }
                for _ in range(16)
            ],
        )
        for chunk_index in range(4)
    ]

    before_four = runtime.classify_training_family_saturation(summaries[:3])
    saturated = runtime.classify_training_family_saturation(summaries)
    tied = copy.deepcopy(summaries)
    tied[-1]["diagnostic_rows"][-1]["raw_score_max_family_ids"] = ["skip", "take"]

    assert before_four["saturated"] is False
    assert saturated["saturated"] is True
    assert saturated["categories"]["card_reward"] == {
        "multi_family_decisions": 64,
        "saturated": True,
        "saturated_family": "take",
        "singleton_max_family_rate": 1.0,
    }
    assert runtime.classify_training_family_saturation(tied)["saturated"] is False


def test_canary_gate_accepts_complete_family_state_and_structural_evidence():
    result = runtime.classify_canary_evaluation(_passing_evaluation())

    assert result["passed"] is True
    assert result["blockers"] == []


def test_canary_gate_rejects_bootstrap_control_drift():
    evaluation = _passing_evaluation()
    evaluation["floor_difference_ci"]["resamples"] = 9_999

    with pytest.raises(runtime.RuntimeBlocked, match="bootstrap"):
        runtime.classify_canary_evaluation(evaluation)


def test_canary_failure_never_constructs_a_holdout_environment():
    touched: list[int] = []

    result = runtime.run_conditional_evaluation(
        runtime.initialize_training_runtime().model,
        runtime.initialize_training_runtime().model,
        environment_factory=lambda seed: touched.append(seed) or OneStepEnvironment(seed),
        canary_seeds=(40, 41, 42, 43),
        holdout_seeds=(50, 51, 52, 53),
    )

    assert result["canary_gate"]["passed"] is False
    assert result["holdout"] == {"accessed": False, "episode_count": 0}
    assert not set(touched).intersection({50, 51, 52, 53})


def test_holdout_reapplies_support_state_family_and_victory_gates(monkeypatch):
    calls: list[str] = []
    canary = _passing_evaluation("canary")
    holdout = _passing_evaluation("holdout")
    holdout["initial"]["unsupported_episodes"] = 1
    holdout["unsupported_rate"] = 0.5
    preserved: list[dict[str, object]] = []
    holdout_started: list[bool] = []

    def fake_paired(*args, cohort, **kwargs):
        calls.append(cohort)
        return copy.deepcopy(canary if cohort == "canary" else holdout)

    monkeypatch.setattr(runtime, "paired_policy_evaluation", fake_paired)

    result = runtime.run_conditional_evaluation(
        object(),
        object(),
        environment_factory=lambda seed: None,
        canary_seeds=(60, 61),
        holdout_seeds=(70, 71),
        on_canary_complete=lambda result: preserved.append(copy.deepcopy(result)),
        on_holdout_start=lambda: holdout_started.append(True),
    )

    assert calls == ["canary", "holdout"]
    assert preserved[0]["verdict"] == "canary_passed_pending_holdout"
    assert preserved[0]["holdout"] == {"accessed": False, "episode_count": 0}
    assert holdout_started == [True]
    assert result["holdout"]["accessed"] is True
    assert result["holdout"]["gate"]["passed"] is False
    assert "unsupported_rate" in result["holdout"]["gate"]["blockers"]
    assert result["verdict"] == "experiment_valid_without_learning_signal"


def test_structurally_invalid_holdout_is_experiment_invalid(monkeypatch):
    canary = _passing_evaluation("canary")
    holdout = _passing_evaluation("holdout")
    holdout["trained"]["replay_exact"] = False

    monkeypatch.setattr(
        runtime,
        "paired_policy_evaluation",
        lambda *args, cohort, **kwargs: copy.deepcopy(
            canary if cohort == "canary" else holdout
        ),
    )

    result = runtime.run_conditional_evaluation(
        object(),
        object(),
        environment_factory=lambda seed: None,
        canary_seeds=(80, 81),
        holdout_seeds=(90, 91),
    )

    assert result["holdout"]["gate"]["passed"] is False
    assert "exact_replay" in result["holdout"]["gate"]["blockers"]
    assert result["verdict"] == "experiment_invalid"


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {
                "complete": True,
                "structural_valid": True,
                "behavior_valid": True,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 1,
            },
            "experiment_valid_with_victory_signal",
        ),
        (
            {
                "complete": True,
                "structural_valid": True,
                "behavior_valid": True,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 0,
            },
            "experiment_valid_with_floor_only_signal",
        ),
        (
            {
                "complete": True,
                "structural_valid": True,
                "behavior_valid": False,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 1,
            },
            "experiment_valid_without_learning_signal",
        ),
        (
            {
                "complete": True,
                "structural_valid": True,
                "behavior_valid": True,
                "floor_signal": True,
                "initial_victories": 1,
                "trained_victories": 0,
            },
            "experiment_valid_without_learning_signal",
        ),
        (
            {
                "complete": True,
                "structural_valid": False,
                "behavior_valid": True,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 1,
            },
            "experiment_invalid",
        ),
        (
            {
                "complete": False,
                "structural_valid": True,
                "behavior_valid": True,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 1,
                "blocked": True,
            },
            "experiment_blocked",
        ),
    ],
)
def test_terminal_verdict_precedence(kwargs, expected):
    assert runtime.classify_terminal_verdict(**kwargs) == expected
