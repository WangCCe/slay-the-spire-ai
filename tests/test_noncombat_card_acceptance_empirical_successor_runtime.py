from __future__ import annotations

import copy
from dataclasses import replace
import importlib
import json

import pytest
import torch

from analysis_scripts.noncombat_card_acceptance_objective import (
    build_card_acceptance_policy_terms,
)
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    HASH_DIM,
    project_state_conditioned_policy_input,
)
from analysis_scripts.noncombat_state_conditioned_ranker import (
    DEFAULT_HIDDEN_DIM,
    StateConditionedCandidateRanker,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    build_transition,
)


RUNTIME_MODULE = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime"
)


def _runtime():
    return importlib.import_module(RUNTIME_MODULE)


def _candidates() -> list[dict[str, object]]:
    return [
        {
            "action_id": "bowl",
            "available": True,
            "category": "card_reward",
            "kind": "bowl",
            "label": "Singing Bowl",
            "raw": {},
        },
        {
            "action_id": "take-a",
            "available": True,
            "category": "card_reward",
            "kind": "take",
            "label": "Take A",
            "raw": {},
        },
        {
            "action_id": "take-b",
            "available": True,
            "category": "card_reward",
            "kind": "take",
            "label": "Take B",
            "raw": {},
        },
    ]


def _features(input_dim: int = HASH_DIM) -> tuple[torch.Tensor, torch.Tensor]:
    state = torch.linspace(-0.5, 0.5, input_dim, dtype=torch.float32)
    candidates = torch.stack(
        (
            torch.linspace(0.1, 0.3, input_dim, dtype=torch.float32),
            torch.linspace(-0.2, 0.4, input_dim, dtype=torch.float32),
            torch.linspace(0.6, -0.1, input_dim, dtype=torch.float32),
        )
    )
    return state, candidates


def _rankers(bootstrap):
    return (
        bootstrap.candidate.card_policy.family_head,
        bootstrap.candidate.card_policy.conditional_ranker,
        bootstrap.candidate.frozen_noncard_ranker,
        bootstrap.control.shared_card_ranker,
        bootstrap.control.frozen_noncard_ranker,
    )


def _has_nonzero(gradients) -> bool:
    return any(
        gradient is not None and bool(torch.count_nonzero(gradient).item())
        for gradient in gradients
    )


def _encoded_mapping_value(encoded: dict[str, object], key: str) -> dict[str, object]:
    assert encoded["type"] == "mapping"
    for item in encoded["items"]:  # type: ignore[union-attr]
        if item["key"] == {"type": "scalar", "value": key}:
            return item["value"]
    raise AssertionError(f"missing encoded mapping key: {key}")


def _candidate_objective(runtime, bootstrap, advantage: float = 1.0):
    state_features, candidate_features = _features()
    output = runtime.forward_card_policy(
        bootstrap,
        arm="candidate",
        state_features=state_features,
        candidate_features=candidate_features,
        candidates=_candidates(),
    )
    terms = build_card_acceptance_policy_terms(
        output.family_logits,
        output.conditional_logits,
        _candidates(),
        "take-b",
        category="card_reward",
    )
    return runtime.build_arm_card_reward_objective(((terms, advantage),))


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


def _rollout_candidates(category: str) -> list[dict[str, object]]:
    if category == "card_reward":
        rows = (
            ("bowl", "bowl", "Singing Bowl"),
            ("take-a", "take", "Take A"),
            ("take-b", "take", "Take B"),
        )
    elif category == "route":
        rows = (
            ("left", "monster", "Left"),
            ("right", "elite", "Right"),
        )
    else:
        raise AssertionError(f"unsupported test category: {category}")
    return [
        {
            "action_id": action_id,
            "available": True,
            "category": category,
            "kind": kind,
            "label": label,
            "raw": {},
        }
        for action_id, kind, label in rows
    ]


class _RolloutEnvironment:
    def __init__(self, seed: int, categories: tuple[str, ...]) -> None:
        self.seed = seed
        self.categories = categories
        self.index = 0

    def snapshot(self) -> dict[str, object]:
        terminal = self.index == len(self.categories)
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {"history": [], "policy_id": "test-control"},
            "category": None if terminal else self.categories[self.index],
            "decision_count": self.index,
            "schema_version": STATE_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "state": {
                "cur_hp": 80,
                "floor": self.index,
                "gold": 100 + self.seed,
                "outcome": "player_loss" if terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": terminal,
        }

    def legal_actions(self) -> list[dict[str, object]]:
        if self.index == len(self.categories):
            return []
        return _rollout_candidates(self.categories[self.index])

    def clone(self):
        return copy.deepcopy(self)

    def step(self, action_id: str) -> dict[str, object]:
        before = self.snapshot()
        candidates = self.legal_actions()
        if action_id not in {row["action_id"] for row in candidates}:
            raise RuntimeError("illegal test action")
        self.index += 1
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=action_id,
            after=self.snapshot(),
            provenance=_rollout_provenance(),
        )


def _synthetic_paired_rollouts(runtime, bootstrap):
    state_features, candidate_features = _features()
    arm_terms = {}
    for arm in ("candidate", "control"):
        output = runtime.forward_card_policy(
            bootstrap,
            arm=arm,
            state_features=state_features,
            candidate_features=candidate_features,
            candidates=_candidates(),
        )
        arm_terms[arm] = build_card_acceptance_policy_terms(
            output.family_logits,
            output.conditional_logits,
            _candidates(),
            "take-b",
            category="card_reward",
        )

    pairs = []
    for position, seed in enumerate(range(100, 164)):
        episodes = {}
        for arm in ("candidate", "control"):
            features = torch.zeros(HASH_DIM, dtype=torch.float32)
            features[position % 128] = 1.0 + 0.01 * position
            reward = (
                0.2 + 0.1 * (position % 5)
                if arm == "candidate"
                else 0.1 + 0.1 * (position % 3)
            )
            decision_id = f"{arm}:seed-{seed}:decision-0"
            decision = runtime.ArmRolloutDecision(
                arm=arm,
                category="card_reward",
                decision_id=decision_id,
                decision_index=0,
                selected_action_id="take-b",
                state_features=features,
                card_terms=arm_terms[arm],
                diagnostic={},
            )
            episodes[arm] = runtime.ArmEpisodeRollout(
                arm=arm,
                seed=seed,
                trajectory_id=f"{arm}:seed-{seed}",
                decisions=(decision,),
                transitions=({"synthetic": True},),
                rewards=(reward,),
                final_snapshot={"terminal": True},
                floor_progress=reward,
                terminal_victory=0,
                unsupported_reason=None,
            )
        pairs.append(
            runtime.PairedEpisodeRollout(
                seed=seed,
                candidate=episodes["candidate"],
                control=episodes["control"],
            )
        )
    return tuple(pairs)


def test_matched_bootstrap_copies_one_base_into_five_storage_disjoint_rankers():
    runtime = _runtime()

    bootstrap = runtime.build_matched_bootstrap()
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(0)
        base = StateConditionedCandidateRanker(HASH_DIM, DEFAULT_HIDDEN_DIM)
    base_state = base.state_dict()

    pointers: set[int] = set()
    for ranker in _rankers(bootstrap):
        assert tuple(ranker.state_dict()) == tuple(base_state)
        for key, tensor in ranker.state_dict().items():
            assert torch.equal(tensor, base_state[key])
            pointer = tensor.untyped_storage().data_ptr()
            assert pointer not in pointers
            pointers.add(pointer)

    assert all(
        not parameter.requires_grad
        for parameter in bootstrap.candidate.frozen_noncard_ranker.parameters()
    )
    assert all(
        not parameter.requires_grad
        for parameter in bootstrap.control.frozen_noncard_ranker.parameters()
    )


def test_matched_bootstrap_forces_cpu_float32_despite_ambient_default_dtype():
    runtime = _runtime()
    ordinary = runtime.build_matched_bootstrap()
    ordinary_payload = runtime.encode_paired_bootstrap(ordinary)
    original_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float64)
        hostile = runtime.build_matched_bootstrap()
        hostile_payload = runtime.encode_paired_bootstrap(hostile)
    finally:
        torch.set_default_dtype(original_dtype)

    assert hostile_payload == ordinary_payload
    for ranker in _rankers(hostile):
        assert all(tensor.device.type == "cpu" for tensor in ranker.state_dict().values())
        assert all(tensor.dtype == torch.float32 for tensor in ranker.state_dict().values())


def test_paired_bootstrap_checkpoint_is_canonical_and_restores_every_ranker_and_rng():
    runtime = _runtime()
    first = runtime.build_matched_bootstrap()
    second = runtime.build_matched_bootstrap()

    first_payload = runtime.encode_paired_bootstrap(first)
    second_payload = runtime.encode_paired_bootstrap(second)
    restored = runtime.restore_paired_bootstrap(first_payload)

    assert isinstance(first_payload, bytes)
    assert first_payload == second_payload
    assert runtime.encode_paired_bootstrap(restored) == first_payload
    assert tuple(first.generators) == (
        "candidate_card",
        "candidate_noncard",
        "control_card",
        "control_noncard",
    )
    for name in first.generators:
        assert first.generators[name] is not second.generators[name]
        assert torch.equal(
            first.generators[name].get_state(), second.generators[name].get_state()
        )

    with pytest.raises(runtime.SuccessorRuntimeError, match="canonical|JSON"):
        runtime.restore_paired_bootstrap(first_payload + b" ")
    with pytest.raises(runtime.SuccessorRuntimeError, match="fields"):
        runtime.restore_paired_bootstrap(
            first_payload[:-1] + b',"unknown":true}'
        )
    dtype_drift = json.loads(first_payload)
    family_state = dtype_drift["models"]["candidate"]["family_head"]
    family_state[next(iter(family_state))]["dtype"] = "float64"
    drift_payload = json.dumps(
        dtype_drift,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    with pytest.raises(runtime.SuccessorRuntimeError, match="dtype|float32"):
        runtime.restore_paired_bootstrap(drift_payload)


def test_runtime_metadata_independently_matches_control_and_is_mutation_safe():
    runtime = _runtime()
    control = importlib.import_module(
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
    )

    metadata = runtime.runtime_metadata()

    assert metadata == control.expected_runtime_metadata()
    metadata["algorithm"]["learning_rate"] = 9.0
    assert runtime.runtime_metadata()["algorithm"]["learning_rate"] == 0.001


def test_four_component_loss_uses_card_decision_mean_and_equal_family_entropy_mean():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    state_features, candidate_features = _features()
    output = runtime.forward_card_policy(
        bootstrap,
        arm="candidate",
        state_features=state_features,
        candidate_features=candidate_features,
        candidates=_candidates(),
    )
    first = build_card_acceptance_policy_terms(
        output.family_logits,
        output.conditional_logits,
        _candidates(),
        "take-a",
        category="card_reward",
    )
    second = build_card_acceptance_policy_terms(
        output.family_logits + torch.tensor([0.2, -0.1]),
        output.conditional_logits + torch.tensor([0.1, -0.2, 0.3]),
        _candidates(),
        "bowl",
        category="card_reward",
    )
    rows = ((first, 1.5), (second, -0.25))

    objective = runtime.build_arm_card_reward_objective(rows)

    expected_family = torch.stack(
        (
            -1.5 * first.selected_family_log_probability,
            0.25 * second.selected_family_log_probability,
        )
    ).mean()
    expected_conditional = torch.stack(
        (
            -1.5 * first.selected_conditional_log_probability,
            0.25 * second.selected_conditional_log_probability,
        )
    ).mean()
    expected_family_entropy = -0.01 * torch.stack(
        (first.family_entropy, second.family_entropy)
    ).mean()
    expected_conditional_entropy = -0.01 * torch.stack(
        (
            first.per_family_conditional_entropies.mean(),
            second.per_family_conditional_entropies.mean(),
        )
    ).mean()

    assert objective.card_decision_count == 2
    assert torch.equal(objective.family_policy_loss, expected_family)
    assert torch.equal(objective.conditional_policy_loss, expected_conditional)
    assert torch.equal(objective.family_entropy_loss, expected_family_entropy)
    assert torch.equal(
        objective.conditional_entropy_loss, expected_conditional_entropy
    )
    assert torch.equal(
        objective.total_loss,
        expected_family
        + expected_conditional
        + expected_family_entropy
        + expected_conditional_entropy,
    )


def test_candidate_objective_components_have_exact_disjoint_head_gradients():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    state_features, candidate_features = _features()
    output = runtime.forward_card_policy(
        bootstrap,
        arm="candidate",
        state_features=state_features,
        candidate_features=candidate_features,
        candidates=_candidates(),
    )
    terms = build_card_acceptance_policy_terms(
        output.family_logits,
        output.conditional_logits,
        _candidates(),
        "take-b",
        category="card_reward",
    )
    objective = runtime.build_arm_card_reward_objective(((terms, 1.0),))
    family_parameters = tuple(bootstrap.candidate.card_policy.family_head.parameters())
    conditional_parameters = tuple(
        bootstrap.candidate.card_policy.conditional_ranker.parameters()
    )
    parameters = family_parameters + conditional_parameters

    family_gradients = torch.autograd.grad(
        objective.family_policy_loss + objective.family_entropy_loss,
        parameters,
        allow_unused=True,
        retain_graph=True,
    )
    conditional_gradients = torch.autograd.grad(
        objective.conditional_policy_loss + objective.conditional_entropy_loss,
        parameters,
        allow_unused=True,
    )
    split = len(family_parameters)

    assert _has_nonzero(family_gradients[:split])
    assert not _has_nonzero(family_gradients[split:])
    assert not _has_nonzero(conditional_gradients[:split])
    assert _has_nonzero(conditional_gradients[split:])


def test_control_family_and_conditional_terms_both_reach_one_shared_card_ranker():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    state_features, candidate_features = _features()
    output = runtime.forward_card_policy(
        bootstrap,
        arm="control",
        state_features=state_features,
        candidate_features=candidate_features,
        candidates=_candidates(),
    )
    terms = build_card_acceptance_policy_terms(
        output.family_logits,
        output.conditional_logits,
        _candidates(),
        "take-a",
        category="card_reward",
    )
    parameters = tuple(bootstrap.control.shared_card_ranker.parameters())

    family_gradients = torch.autograd.grad(
        -terms.selected_family_log_probability,
        parameters,
        retain_graph=True,
    )
    conditional_gradients = torch.autograd.grad(
        -terms.selected_conditional_log_probability,
        parameters,
    )

    assert _has_nonzero(family_gradients)
    assert _has_nonzero(conditional_gradients)


def test_each_arm_has_one_exact_adam_group_and_replayable_moments():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    optimizers = runtime.build_arm_optimizers(bootstrap)

    candidate_expected = {
        id(parameter)
        for module in (
            bootstrap.candidate.card_policy.family_head,
            bootstrap.candidate.card_policy.conditional_ranker,
        )
        for parameter in module.parameters()
    }
    control_expected = {
        id(parameter) for parameter in bootstrap.control.shared_card_ranker.parameters()
    }
    candidate_actual = {
        id(parameter)
        for parameter in optimizers.candidate.param_groups[0]["params"]
    }
    control_actual = {
        id(parameter) for parameter in optimizers.control.param_groups[0]["params"]
    }

    assert len(optimizers.candidate.param_groups) == 1
    assert len(optimizers.control.param_groups) == 1
    assert candidate_actual == candidate_expected
    assert control_actual == control_expected
    for optimizer in (optimizers.candidate, optimizers.control):
        group = optimizer.param_groups[0]
        assert group["lr"] == 0.001
        assert group["betas"] == (0.9, 0.999)
        assert group["eps"] == 1e-8
        assert group["weight_decay"] == 0.0
        assert group["amsgrad"] is False

    optimizers.candidate.zero_grad(set_to_none=True)
    loss = sum(
        parameter.square().sum()
        for parameter in optimizers.candidate.param_groups[0]["params"]
    )
    loss.backward()
    torch.nn.utils.clip_grad_norm_(
        optimizers.candidate.param_groups[0]["params"], 1.0
    )
    optimizers.candidate.step()
    payload = runtime.encode_optimizer_state(optimizers.candidate)

    fresh = runtime.build_matched_bootstrap()
    fresh_optimizers = runtime.build_arm_optimizers(fresh)
    runtime.restore_optimizer_state(fresh_optimizers.candidate, payload)

    assert runtime.encode_optimizer_state(fresh_optimizers.candidate) == payload


def test_optimizer_state_rejects_type_option_and_parameter_order_drift():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    optimizers = runtime.build_arm_optimizers(bootstrap)
    parameters = tuple(optimizers.candidate.param_groups[0]["params"])
    sgd = torch.optim.SGD(parameters, lr=0.001)

    with pytest.raises(runtime.SuccessorRuntimeError, match="Adam|optimizer"):
        runtime.encode_optimizer_state(sgd)

    payload = runtime.encode_optimizer_state(optimizers.candidate)
    changed_lr = copy.deepcopy(payload)
    groups = _encoded_mapping_value(changed_lr, "param_groups")
    first_group = groups["items"][0]  # type: ignore[index]
    _encoded_mapping_value(first_group, "lr")["value"] = 9.0
    with pytest.raises(runtime.SuccessorRuntimeError, match="option|lr|learning"):
        runtime.restore_optimizer_state(optimizers.candidate, changed_lr)

    reordered = copy.deepcopy(payload)
    groups = _encoded_mapping_value(reordered, "param_groups")
    first_group = groups["items"][0]  # type: ignore[index]
    encoded_params = _encoded_mapping_value(first_group, "params")
    encoded_params["items"] = list(reversed(encoded_params["items"]))  # type: ignore[arg-type]
    with pytest.raises(runtime.SuccessorRuntimeError, match="parameter|order"):
        runtime.restore_optimizer_state(optimizers.candidate, reordered)

    boolean_index = copy.deepcopy(payload)
    encoded_state = _encoded_mapping_value(boolean_index, "state")
    encoded_state["items"] = [
        {
            "key": {"type": "scalar", "value": True},
            "value": {"type": "mapping", "items": []},
        }
    ]
    with pytest.raises(runtime.SuccessorRuntimeError, match="parameter index"):
        runtime.restore_optimizer_state(optimizers.candidate, boolean_index)


def test_runtime_step_reconstructs_components_clips_globally_and_replays_moments():
    runtime = _runtime()
    first = runtime.build_matched_bootstrap()
    first_optimizers = runtime.build_arm_optimizers(first)
    first_parameters = tuple(first_optimizers.candidate.param_groups[0]["params"])
    first_objective = _candidate_objective(runtime, first, advantage=1_000_000.0)

    first_evidence = runtime.apply_arm_optimizer_step(
        first_optimizers.candidate,
        first_objective,
        parameters=first_parameters,
    )

    assert first_evidence.component_order == (
        "family_policy",
        "conditional_policy",
        "family_entropy",
        "conditional_entropy",
    )
    assert first_evidence.preclip_global_norm > 1.0
    assert first_evidence.postclip_global_norm <= 1.0 + 1e-6
    assert len(first_evidence.parameter_names) == len(first_parameters)
    assert len(first_evidence.pre_parameters) == len(first_parameters)
    assert len(first_evidence.post_parameters) == len(first_parameters)
    assert any(
        not torch.equal(before, after)
        for before, after in zip(
            first_evidence.pre_parameters,
            first_evidence.post_parameters,
            strict=True,
        )
    )
    for index, combined in enumerate(first_evidence.combined_gradients):
        reconstructed = torch.zeros_like(combined)
        for component in first_evidence.component_gradients:
            gradient = component[index]
            if gradient is not None:
                reconstructed = reconstructed + gradient
        assert torch.equal(combined, reconstructed)

    second = runtime.build_matched_bootstrap()
    second_optimizers = runtime.build_arm_optimizers(second)
    second_parameters = tuple(second_optimizers.candidate.param_groups[0]["params"])
    second_objective = _candidate_objective(runtime, second, advantage=1_000_000.0)
    second_evidence = runtime.apply_arm_optimizer_step(
        second_optimizers.candidate,
        second_objective,
        parameters=second_parameters,
    )

    assert runtime.encode_paired_bootstrap(first) == runtime.encode_paired_bootstrap(
        second
    )
    assert runtime.encode_optimizer_state(
        first_optimizers.candidate
    ) == runtime.encode_optimizer_state(second_optimizers.candidate)
    assert first_evidence.preclip_global_norm == second_evidence.preclip_global_norm
    assert first_evidence.postclip_global_norm == second_evidence.postclip_global_norm


def test_card_sampling_is_family_first_and_arm_generators_are_independent():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    terms = build_card_acceptance_policy_terms(
        torch.tensor([-0.2, 0.7], dtype=torch.float32),
        torch.tensor([0.1, -0.4, 0.9], dtype=torch.float32),
        _candidates(),
        "take-b",
        category="card_reward",
    )
    expected_generator = torch.Generator(device="cpu")
    expected_generator.set_state(
        bootstrap.generators["candidate_card"].get_state().clone()
    )
    family_index = int(
        torch.multinomial(
            terms.family_probabilities,
            1,
            generator=expected_generator,
        ).item()
    )
    selected_family = terms.family_order[family_index]
    candidate_indices = tuple(
        index
        for index, family in enumerate(terms.candidate_families)
        if family == selected_family
    )
    local_probabilities = terms.conditional_probabilities[
        torch.tensor(candidate_indices, dtype=torch.long)
    ]
    local_index = int(
        torch.multinomial(
            local_probabilities,
            1,
            generator=expected_generator,
        ).item()
    )
    expected_action = terms.action_ids[candidate_indices[local_index]]
    untouched_control_state = bootstrap.generators["control_card"].get_state().clone()

    selected = runtime.select_two_stage_action(
        terms,
        generator=bootstrap.generators["candidate_card"],
        greedy=False,
    )

    assert selected == expected_action
    assert torch.equal(
        bootstrap.generators["candidate_card"].get_state(),
        expected_generator.get_state(),
    )
    assert torch.equal(
        bootstrap.generators["control_card"].get_state(), untouched_control_state
    )


def test_unique_greedy_selection_rejects_family_or_conditional_ties():
    runtime = _runtime()
    unique_terms = build_card_acceptance_policy_terms(
        torch.tensor([-0.5, 0.8], dtype=torch.float32),
        torch.tensor([0.0, -0.2, 0.9], dtype=torch.float32),
        _candidates(),
        "take-b",
        category="card_reward",
    )
    family_tied_terms = build_card_acceptance_policy_terms(
        torch.tensor([0.0, 0.0], dtype=torch.float32),
        torch.tensor([0.0, 0.2, 0.9], dtype=torch.float32),
        _candidates(),
        "take-a",
        category="card_reward",
    )
    conditional_tied_terms = build_card_acceptance_policy_terms(
        torch.tensor([-0.5, 0.8], dtype=torch.float32),
        torch.tensor([0.0, 0.2, 0.2], dtype=torch.float32),
        _candidates(),
        "take-a",
        category="card_reward",
    )

    assert runtime.select_two_stage_action(unique_terms, greedy=True) == "take-b"
    with pytest.raises(runtime.SuccessorRuntimeError, match="family.*tie|unique"):
        runtime.select_two_stage_action(family_tied_terms, greedy=True)
    with pytest.raises(
        runtime.SuccessorRuntimeError, match="conditional.*tie|unique"
    ):
        runtime.select_two_stage_action(conditional_tied_terms, greedy=True)


def test_noncard_routing_uses_only_the_frozen_ranker_for_each_arm():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    state_features, candidate_features = _features()

    candidate_logits = runtime.score_noncard_candidates(
        bootstrap,
        arm="candidate",
        category="shop",
        state_features=state_features,
        candidate_features=candidate_features,
    )
    control_logits = runtime.score_noncard_candidates(
        bootstrap,
        arm="control",
        category="route",
        state_features=state_features,
        candidate_features=candidate_features,
    )

    assert torch.equal(
        candidate_logits,
        bootstrap.candidate.frozen_noncard_ranker(
            state_features, candidate_features
        ),
    )
    assert torch.equal(
        control_logits,
        bootstrap.control.frozen_noncard_ranker(state_features, candidate_features),
    )
    with pytest.raises(runtime.SuccessorRuntimeError, match="card_reward"):
        runtime.score_noncard_candidates(
            bootstrap,
            arm="candidate",
            category="card_reward",
            state_features=state_features,
            candidate_features=candidate_features,
        )


@pytest.mark.parametrize(
    ("category", "advanced_generator", "untouched_generator"),
    (
        ("card_reward", "candidate_card", "candidate_noncard"),
        ("route", "candidate_noncard", "candidate_card"),
    ),
)
def test_arm_training_rollout_advances_only_the_category_owned_generator(
    category: str,
    advanced_generator: str,
    untouched_generator: str,
):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    before = {
        name: generator.get_state().clone()
        for name, generator in bootstrap.generators.items()
    }
    expected_route_action: str | None = None
    expected_route_generator_state: torch.Tensor | None = None
    if category == "route":
        environment = _RolloutEnvironment(17, (category,))
        snapshot = environment.snapshot()
        candidates = environment.legal_actions()
        policy_input = project_state_conditioned_policy_input(snapshot, candidates)
        scores = runtime.score_noncard_candidates(
            bootstrap,
            arm="candidate",
            category=category,
            state_features=policy_input.state_features,
            candidate_features=policy_input.candidate_features,
        )
        expected_generator = torch.Generator(device="cpu")
        expected_generator.set_state(before[advanced_generator].clone())
        expected_index = int(
            torch.multinomial(
                torch.softmax(scores, dim=0).detach(),
                1,
                generator=expected_generator,
            ).item()
        )
        expected_route_action = str(candidates[expected_index]["action_id"])
        expected_route_generator_state = expected_generator.get_state().clone()

    rollout = runtime.rollout_arm_training_episode(
        bootstrap,
        arm="candidate",
        environment_factory=lambda seed: _RolloutEnvironment(seed, (category,)),
        seed=17,
    )

    assert rollout.arm == "candidate"
    assert rollout.seed == 17
    assert len(rollout.decisions) == 1
    assert rollout.decisions[0].category == category
    assert (rollout.decisions[0].card_terms is not None) == (
        category == "card_reward"
    )
    assert not torch.equal(
        bootstrap.generators[advanced_generator].get_state(),
        before[advanced_generator],
    )
    assert torch.equal(
        bootstrap.generators[untouched_generator].get_state(),
        before[untouched_generator],
    )
    assert torch.equal(
        bootstrap.generators["control_card"].get_state(),
        before["control_card"],
    )
    assert torch.equal(
        bootstrap.generators["control_noncard"].get_state(),
        before["control_noncard"],
    )
    assert rollout.final_snapshot["terminal"] is True
    assert rollout.terminal_victory == 0
    if category == "route":
        assert rollout.decisions[0].selected_action_id == expected_route_action
        assert expected_route_generator_state is not None
        assert torch.equal(
            bootstrap.generators[advanced_generator].get_state(),
            expected_route_generator_state,
        )


@pytest.mark.parametrize("drift", ("requires_grad", "bytes"))
def test_rollout_rejects_frozen_noncard_drift_before_environment_construction(
    drift: str,
):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    if drift == "requires_grad":
        bootstrap.candidate.frozen_noncard_ranker.requires_grad_(True)
    else:
        with torch.no_grad():
            next(
                bootstrap.candidate.frozen_noncard_ranker.parameters()
            ).add_(1.0)
    factory_calls: list[int] = []

    def environment_factory(seed: int):
        factory_calls.append(seed)
        return _RolloutEnvironment(seed, ("route",))

    with pytest.raises(runtime.SuccessorRuntimeError, match="frozen non-card"):
        runtime.rollout_arm_training_episode(
            bootstrap,
            arm="candidate",
            environment_factory=environment_factory,
            seed=31,
        )

    assert factory_calls == []


def test_paired_training_rollout_uses_same_seed_fixed_arm_order_and_frozen_routing():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    frozen_before = {
        arm: {
            name: tensor.detach().clone()
            for name, tensor in ranker.state_dict().items()
        }
        for arm, ranker in (
            ("candidate", bootstrap.candidate.frozen_noncard_ranker),
            ("control", bootstrap.control.frozen_noncard_ranker),
        )
    }
    factory_calls: list[int] = []

    def environment_factory(seed: int):
        factory_calls.append(seed)
        return _RolloutEnvironment(seed, ("card_reward", "route"))

    paired = runtime.rollout_paired_training_episode(
        bootstrap,
        environment_factory=environment_factory,
        seed=23,
    )

    assert factory_calls == [23, 23]
    assert paired.seed == 23
    assert paired.candidate.arm == "candidate"
    assert paired.control.arm == "control"
    for arm_rollout in (paired.candidate, paired.control):
        assert tuple(row.category for row in arm_rollout.decisions) == (
            "card_reward",
            "route",
        )
        assert arm_rollout.decisions[0].card_terms is not None
        assert arm_rollout.decisions[1].card_terms is None
        assert len(arm_rollout.transitions) == 2
        assert arm_rollout.floor_progress > 0.0
    assert paired.candidate.floor_progress == paired.control.floor_progress
    assert tuple(
        row.selected_action_id for row in paired.candidate.decisions
    ) == tuple(row.selected_action_id for row in paired.control.decisions)
    assert torch.equal(
        bootstrap.generators["candidate_card"].get_state(),
        bootstrap.generators["control_card"].get_state(),
    )
    assert torch.equal(
        bootstrap.generators["candidate_noncard"].get_state(),
        bootstrap.generators["control_noncard"].get_state(),
    )
    for arm, ranker in (
        ("candidate", bootstrap.candidate.frozen_noncard_ranker),
        ("control", bootstrap.control.frozen_noncard_ranker),
    ):
        for name, tensor in ranker.state_dict().items():
            assert torch.equal(tensor, frozen_before[arm][name])


def test_state_only_baseline_folding_is_fixed_float32_modulo_128():
    runtime = _runtime()
    source = torch.ones(HASH_DIM, dtype=torch.float32)

    folded = runtime.fold_baseline_state_features(source)

    assert folded.shape == (128,)
    assert folded.dtype == torch.float32
    assert folded.device.type == "cpu"
    assert torch.equal(folded, torch.full((128,), 8.0, dtype=torch.float32))
    with pytest.raises(runtime.SuccessorRuntimeError, match="1024|shape"):
        runtime.fold_baseline_state_features(source[:-1])
    with pytest.raises(runtime.SuccessorRuntimeError, match="float32|dtype"):
        runtime.fold_baseline_state_features(source.to(dtype=torch.float64))


def test_paired_cross_fitted_baselines_are_arm_local_and_advantages_are_unscaled():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    pairs = _synthetic_paired_rollouts(runtime, bootstrap)

    baselines = runtime.build_paired_cross_fitted_baselines(pairs)

    assert baselines.seeds == tuple(range(100, 164))
    for arm, baseline in (
        ("candidate", baselines.candidate),
        ("control", baselines.control),
    ):
        assert baseline.arm == arm
        assert len(baseline.decisions) == 64
        assert len(baseline.models) == 4
        assert len(baseline.predictions) == 64
        assert len(baseline.advantage_batch.records) == 64
        for model in baseline.models:
            assert len(model.held_out_trajectory_ids) == 16
            assert len(model.fit_trajectory_ids) == 48
            assert set(model.held_out_trajectory_ids).isdisjoint(
                model.fit_trajectory_ids
            )
        rows = runtime.build_arm_card_reward_rows(
            pairs,
            arm=arm,
            baseline=baseline,
        )
        records = {
            record.decision_id: record
            for record in baseline.advantage_batch.records
        }
        assert len(rows) == 64
        for decision, (terms, advantage) in zip(
            baseline.decisions, rows, strict=True
        ):
            record = records[decision.decision_id]
            assert terms.selected_action_id == "take-b"
            assert advantage == record.advantage
            assert advantage == record.raw_return - record.baseline_prediction
            assert record.scale_mode == "fixed_unit"
            assert record.scale == 1.0
            assert record.scale_fit_trajectory_ids == ()
    assert tuple(
        prediction.clipped for prediction in baselines.candidate.predictions
    ) != tuple(prediction.clipped for prediction in baselines.control.predictions)


def test_cross_fitted_baseline_rejects_incomplete_reordered_or_unsupported_pairs():
    runtime = _runtime()
    pairs = _synthetic_paired_rollouts(
        runtime,
        runtime.build_matched_bootstrap(),
    )

    with pytest.raises(runtime.SuccessorRuntimeError, match="exactly 64"):
        runtime.build_paired_cross_fitted_baselines(pairs[:-1])
    with pytest.raises(runtime.SuccessorRuntimeError, match="ascending"):
        runtime.build_paired_cross_fitted_baselines(tuple(reversed(pairs)))

    unsupported_candidate = replace(
        pairs[0].candidate,
        unsupported_reason="unsupported_shop_courier_restock_semantics",
    )
    unsupported_pairs = (
        replace(pairs[0], candidate=unsupported_candidate),
        *pairs[1:],
    )
    with pytest.raises(
        runtime.SuccessorRuntimeError,
        match="complete supported trajectories",
    ):
        runtime.build_paired_cross_fitted_baselines(unsupported_pairs)


def test_paired_chunk_update_applies_one_named_step_per_arm_and_preserves_frozen_state():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    optimizers = runtime.build_arm_optimizers(bootstrap)
    pairs = _synthetic_paired_rollouts(runtime, bootstrap)
    frozen_before = {
        arm: {
            name: tensor.detach().clone()
            for name, tensor in ranker.state_dict().items()
        }
        for arm, ranker in (
            ("candidate", bootstrap.candidate.frozen_noncard_ranker),
            ("control", bootstrap.control.frozen_noncard_ranker),
        )
    }
    generators_before = {
        name: generator.get_state().clone()
        for name, generator in bootstrap.generators.items()
    }

    update = runtime.apply_paired_cross_fitted_chunk_update(
        bootstrap,
        optimizers,
        pairs,
    )

    assert update.seeds == tuple(range(100, 164))
    assert update.candidate.arm == "candidate"
    assert update.control.arm == "control"
    assert update.candidate.objective.card_decision_count == 64
    assert update.control.objective.card_decision_count == 64
    assert all(
        name.startswith(("family_head.", "conditional_ranker."))
        for name in update.candidate.optimizer_step.parameter_names
    )
    assert all(
        name.startswith("shared_card_ranker.")
        for name in update.control.optimizer_step.parameter_names
    )
    for arm_update in (update.candidate, update.control):
        step = arm_update.optimizer_step
        assert any(
            not torch.equal(before, after)
            for before, after in zip(
                step.pre_parameters,
                step.post_parameters,
                strict=True,
            )
        )
        assert step.postclip_global_norm <= 1.0 + 1e-6
    assert runtime.encode_optimizer_state(optimizers.candidate) == (
        update.candidate.optimizer_step.optimizer_state_after
    )
    assert runtime.encode_optimizer_state(optimizers.control) == (
        update.control.optimizer_step.optimizer_state_after
    )
    for arm, ranker in (
        ("candidate", bootstrap.candidate.frozen_noncard_ranker),
        ("control", bootstrap.control.frozen_noncard_ranker),
    ):
        for name, tensor in ranker.state_dict().items():
            assert torch.equal(tensor, frozen_before[arm][name])
    for name, generator in bootstrap.generators.items():
        assert torch.equal(generator.get_state(), generators_before[name])


def test_paired_chunk_validates_both_arms_before_the_candidate_step():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    optimizers = runtime.build_arm_optimizers(bootstrap)
    pairs = _synthetic_paired_rollouts(runtime, bootstrap)
    bootstrap_before = runtime.encode_paired_bootstrap(bootstrap)
    candidate_optimizer_before = runtime.encode_optimizer_state(
        optimizers.candidate
    )
    optimizers.control.param_groups[0]["lr"] = 9.0

    with pytest.raises(runtime.SuccessorRuntimeError, match="option|lr"):
        runtime.apply_paired_cross_fitted_chunk_update(
            bootstrap,
            optimizers,
            pairs,
        )

    assert runtime.encode_paired_bootstrap(bootstrap) == bootstrap_before
    assert (
        runtime.encode_optimizer_state(optimizers.candidate)
        == candidate_optimizer_before
    )
    assert all(
        parameter.grad is None
        for parameter in optimizers.candidate.param_groups[0]["params"]
    )
    assert all(
        parameter.grad is None
        for parameter in optimizers.control.param_groups[0]["params"]
    )


def test_card_objective_rejects_a_zero_card_reward_chunk():
    runtime = _runtime()

    with pytest.raises(runtime.SuccessorRuntimeError, match="requires decisions"):
        runtime.build_arm_card_reward_objective(())
