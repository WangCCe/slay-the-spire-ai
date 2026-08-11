from __future__ import annotations

import copy
from dataclasses import replace
import gzip
import hashlib
import importlib
import json
import math
import random

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


def test_registered_zero_progress_checkpoint_matches_runner_snapshot_format():
    runtime = _runtime()
    runner = importlib.import_module(
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_training_runner"
    )

    checkpoint = runtime.encode_paired_training_checkpoint(
        runtime.initialize_paired_training_runtime()
    )
    snapshot = runner._checkpoint_snapshot(checkpoint)

    assert not checkpoint.endswith(b"\n")
    assert set(snapshot["coordinates"].values()) == {0}
    assert snapshot["checkpoint_sha256"] == hashlib.sha256(checkpoint).hexdigest()
    assert snapshot["stopped_for_family_saturation"] is False


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
    return _arm_objective(runtime, bootstrap, arm="candidate", advantage=advantage)


def _arm_objective(runtime, bootstrap, *, arm: str, advantage: float = 1.0):
    state_features, candidate_features = _features()
    output = runtime.forward_card_policy(
        bootstrap,
        arm=arm,
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


def _synthetic_paired_rollouts(runtime, bootstrap, *, start_seed: int = 100):
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
    for position, seed in enumerate(range(start_seed, start_seed + 64)):
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


def _canary_arm_rollout(runtime, *, arm: str, seed: int, family: str):
    if family == "bowl":
        family_logits = torch.tensor([2.0, -2.0], dtype=torch.float32)
        selected_action_id = "bowl"
    elif family == "take":
        family_logits = torch.tensor([-2.0, 2.0], dtype=torch.float32)
        selected_action_id = "take-b"
    else:
        raise AssertionError(family)
    terms = build_card_acceptance_policy_terms(
        family_logits,
        torch.tensor([0.0, -1.0, 1.0], dtype=torch.float32),
        _candidates(),
        selected_action_id,
        category="card_reward",
    )
    decision = runtime.ArmRolloutDecision(
        arm=arm,
        category="card_reward",
        decision_id=f"{arm}:seed-{seed}:decision-0",
        decision_index=0,
        selected_action_id=selected_action_id,
        state_features=torch.zeros(HASH_DIM, dtype=torch.float32),
        card_terms=terms,
        diagnostic={
            "family_order": list(terms.family_order),
            "multi_family": True,
            "selected_family": terms.selected_family,
            "unique_greedy_family_id": terms.unique_greedy_family_id,
        },
    )
    return runtime.ArmEpisodeRollout(
        arm=arm,
        seed=seed,
        trajectory_id=f"{arm}:seed-{seed}",
        decisions=(decision,),
        transitions=(),
        rewards=(0.0,),
        final_snapshot={
            "state": {"outcome": "player_loss", "seed": str(seed)},
            "terminal": True,
        },
        floor_progress=0.0,
        terminal_victory=0,
        unsupported_reason=None,
    )


def _canary_pair(runtime, seed: int, *, family: str | None = None):
    selected_family = family or ("bowl" if seed % 2 == 0 else "take")
    return runtime.PairedEpisodeRollout(
        seed=seed,
        candidate=_canary_arm_rollout(
            runtime,
            arm="candidate",
            seed=seed,
            family=selected_family,
        ),
        control=_canary_arm_rollout(
            runtime,
            arm="control",
            seed=seed,
            family=selected_family,
        ),
    )


def _canary_arm_bindings():
    return {
        "candidate": {
            "checkpoint_sha256": "1" * 64,
            "configuration_sha256": "2" * 64,
            "source_sha256": "3" * 64,
        },
        "control": {
            "checkpoint_sha256": "4" * 64,
            "configuration_sha256": "5" * 64,
            "source_sha256": "3" * 64,
        },
    }


def _verified_canary_binding():
    return {
        "terminal_sha256": "6" * 64,
        "verdict": "canary_passed",
        "verified": True,
    }


def _holdout_pair(
    runtime,
    seed: int,
    *,
    family: str | None = None,
    candidate_floor: float = 1.0,
    control_floor: float = 0.0,
    candidate_victory: int = 1,
    control_victory: int = 0,
):
    pair = _canary_pair(runtime, seed, family=family)

    def updated(rollout, floor_progress: float, victory: int):
        outcome = "player_victory" if victory else "player_loss"
        return replace(
            rollout,
            final_snapshot={
                "state": {"outcome": outcome, "seed": str(seed)},
                "terminal": True,
            },
            floor_progress=floor_progress,
            rewards=(floor_progress,),
            terminal_victory=victory,
        )

    return runtime.PairedEpisodeRollout(
        seed=seed,
        candidate=updated(pair.candidate, candidate_floor, candidate_victory),
        control=updated(pair.control, control_floor, control_victory),
    )


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


def test_paired_frozen_evaluation_is_greedy_repeatable_and_state_immutable():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    before = runtime.encode_paired_bootstrap(bootstrap)

    first = runtime.rollout_paired_frozen_evaluation(
        bootstrap,
        environment_factory=lambda seed: _RolloutEnvironment(
            seed, ("card_reward", "route")
        ),
        seed=29,
    )
    second = runtime.rollout_paired_frozen_evaluation(
        bootstrap,
        environment_factory=lambda seed: _RolloutEnvironment(
            seed, ("card_reward", "route")
        ),
        seed=29,
    )

    assert runtime.encode_paired_bootstrap(bootstrap) == before
    for arm_first, arm_second in (
        (first.candidate, second.candidate),
        (first.control, second.control),
    ):
        assert tuple(
            decision.selected_action_id for decision in arm_first.decisions
        ) == tuple(
            decision.selected_action_id for decision in arm_second.decisions
        )
        card = arm_first.decisions[0]
        route = arm_first.decisions[1]
        assert card.card_terms is not None
        assert card.selected_action_id == (
            card.card_terms.unique_two_stage_greedy_action_id
        )
        maximum_ids = route.diagnostic["raw_score_max_action_ids"]
        assert maximum_ids == [route.selected_action_id]
        assert arm_first.final_snapshot == arm_second.final_snapshot


def test_frozen_noncard_evaluation_rejects_raw_score_ties():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    with torch.no_grad():
        for ranker in (
            bootstrap.candidate.frozen_noncard_ranker,
            bootstrap.control.frozen_noncard_ranker,
        ):
            for parameter in ranker.parameters():
                parameter.zero_()

    with pytest.raises(
        runtime.SuccessorRuntimeError,
        match="non-card.*tie|raw-score.*tie|unique",
    ):
        runtime.rollout_paired_frozen_evaluation(
            bootstrap,
            environment_factory=lambda seed: _RolloutEnvironment(seed, ("route",)),
            seed=31,
        )


def test_successor_resource_ledger_keeps_training_and_shadow_steps_distinct():
    runtime = _runtime()

    ledger = runtime.build_successor_resource_ledger(
        training_environment_accesses=1_024,
        training_optimizer_steps=16,
        shadow_optimizer_steps=1,
        canary_environment_accesses=512,
        holdout_environment_accesses=1_024,
    )

    assert ledger == {
        "canary_environment_accesses": 512,
        "holdout_environment_accesses": 1_024,
        "shadow_optimizer_steps": 1,
        "total_environment_accesses": 2_560,
        "total_optimizer_steps": 17,
        "training_environment_accesses": 1_024,
        "training_optimizer_steps": 16,
    }
    with pytest.raises(runtime.SuccessorRuntimeError, match="shadow"):
        runtime.build_successor_resource_ledger(
            training_environment_accesses=0,
            training_optimizer_steps=0,
            shadow_optimizer_steps=2,
            canary_environment_accesses=0,
            holdout_environment_accesses=0,
        )


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
    training = runtime.initialize_paired_training_runtime()
    bootstrap = training.bootstrap
    optimizers = training.optimizers
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

    completed = runtime.complete_paired_training_chunk(
        training,
        pairs,
        chunk_index=0,
    )
    update = completed.update

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
    assert training.next_chunk_index == 1
    assert training.completed_pairs == 64
    assert training.training_environment_accesses == 128
    assert training.candidate_optimizer_updates == 1
    assert training.control_optimizer_updates == 1
    assert training.training_optimizer_steps == 2
    assert completed.saturation["stop"] is False
    assert completed.checkpoint == runtime.encode_paired_training_checkpoint(
        training
    )
    restored = runtime.restore_paired_training_checkpoint(completed.checkpoint)
    assert runtime.encode_paired_training_checkpoint(restored) == (
        completed.checkpoint
    )
    drift = json.loads(completed.checkpoint)
    drift["coordinates"]["completed_pairs"] = 65
    drift_payload = json.dumps(
        drift,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    with pytest.raises(runtime.SuccessorRuntimeError, match="resource coordinates"):
        runtime.restore_paired_training_checkpoint(drift_payload)


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


def _family_summary_chunk(
    chunk_index: int,
    families: tuple[str | None, ...],
) -> dict[str, object]:
    return {
        "candidate_card_decisions": [
            {
                "multi_family": True,
                "unique_greedy_family_id": family,
            }
            for family in families
        ],
        "chunk_index": chunk_index,
    }


def _advance_training_coordinate_step(
    runtime,
    training,
    *,
    chunk_index: int,
    families: tuple[str | None, ...],
) -> None:
    for arm, optimizer in (
        ("candidate", training.optimizers.candidate),
        ("control", training.optimizers.control),
    ):
        runtime.apply_arm_optimizer_step(
            optimizer,
            _arm_objective(
                runtime,
                training.bootstrap,
                arm=arm,
                advantage=1.0,
            ),
            parameters=tuple(optimizer.param_groups[0]["params"]),
        )
    training.completed_chunk_summaries.append(
        _family_summary_chunk(chunk_index, families)
    )
    training.next_chunk_index += 1
    training.completed_pairs += 64
    training.completed_decisions += 128
    training.training_environment_accesses += 128
    training.candidate_optimizer_updates += 1
    training.control_optimizer_updates += 1
    training.training_optimizer_steps += 2


def test_candidate_family_saturation_is_ineligible_before_four_complete_chunks():
    runtime = _runtime()
    chunks = tuple(
        _family_summary_chunk(index, ("take",) * 64)
        for index in range(3)
    )

    result = runtime.classify_candidate_family_saturation(chunks)

    assert result == {
        "family": None,
        "multi_family_decisions": 0,
        "stop": False,
        "window_chunk_indices": [0, 1, 2],
    }


def test_candidate_family_saturation_first_triggers_at_exact_four_chunk_boundary():
    runtime = _runtime()
    chunks = tuple(
        _family_summary_chunk(index, ("take",) * 16)
        for index in range(4)
    )

    result = runtime.classify_candidate_family_saturation(chunks)

    assert result == {
        "family": "take",
        "multi_family_decisions": 64,
        "stop": True,
        "window_chunk_indices": [0, 1, 2, 3],
    }


def test_candidate_family_saturation_allows_exact_eight_chunk_mixed_completion():
    runtime = _runtime()
    chunks = tuple(
        _family_summary_chunk(
            index,
            tuple("take" if offset % 2 == 0 else "bowl" for offset in range(16)),
        )
        for index in range(8)
    )

    results = tuple(
        runtime.classify_candidate_family_saturation(chunks[:count])
        for count in range(1, 9)
    )

    assert all(result["stop"] is False for result in results)
    assert results[-1]["window_chunk_indices"] == [4, 5, 6, 7]


def test_training_collection_uses_write_ahead_candidate_then_control_hooks(
    monkeypatch,
):
    runtime = _runtime()
    training = runtime.initialize_paired_training_runtime()
    synthetic_pairs = _synthetic_paired_rollouts(
        runtime,
        training.bootstrap,
        start_seed=200,
    )
    episode_by_identity = {
        (arm, pair.seed): (
            pair.candidate if arm == "candidate" else pair.control
        )
        for pair in synthetic_pairs
        for arm in ("candidate", "control")
    }
    hook_calls: list[tuple[str, str, int]] = []
    factory_calls: list[int] = []

    def environment_factory(seed: int):
        factory_calls.append(seed)
        return _RolloutEnvironment(seed, ("card_reward",))

    def rollout_stub(
        bootstrap,
        *,
        arm,
        environment_factory,
        seed,
        **_kwargs,
    ):
        environment_factory(seed)
        return episode_by_identity[(arm, seed)]

    monkeypatch.setattr(runtime, "rollout_arm_training_episode", rollout_stub)

    completed = runtime.collect_and_complete_paired_training_chunk(
        training,
        environment_factory=environment_factory,
        seeds=tuple(range(200, 264)),
        chunk_index=0,
        before_environment=lambda arm, seed: hook_calls.append(
            ("before", arm, seed)
        ),
        after_environment=lambda arm, seed: hook_calls.append(
            ("after", arm, seed)
        ),
        deadline=100.0,
        clock=lambda: 0.0,
    )

    assert factory_calls == [seed for seed in range(200, 264) for _ in range(2)]
    assert hook_calls[:4] == [
        ("before", "candidate", 200),
        ("after", "candidate", 200),
        ("before", "control", 200),
        ("after", "control", 200),
    ]
    assert len(hook_calls) == 256
    assert completed.seeds == tuple(range(200, 264))
    assert training.training_environment_accesses == 128
    assert runtime.training_progress_verdict(training) == "training_incomplete"


def test_exact_eight_chunk_coordinates_are_required_for_no_saturation_completion():
    runtime = _runtime()
    training = runtime.initialize_paired_training_runtime()
    mixed_families = tuple(
        "take" if index % 2 == 0 else "bowl" for index in range(16)
    )

    for chunk_index in range(8):
        _advance_training_coordinate_step(
            runtime,
            training,
            chunk_index=chunk_index,
            families=mixed_families,
        )

    assert runtime.training_progress_verdict(training) == (
        "training_completed_without_family_saturation"
    )
    assert training.completed_pairs == 512
    assert training.training_environment_accesses == 1_024
    assert training.candidate_optimizer_updates == 8
    assert training.control_optimizer_updates == 8
    assert training.training_optimizer_steps == 16


def test_family_saturation_keeps_canary_and_holdout_zero_and_blocks_more_training():
    runtime = _runtime()
    training = runtime.initialize_paired_training_runtime()
    for chunk_index in range(4):
        _advance_training_coordinate_step(
            runtime,
            training,
            chunk_index=chunk_index,
            families=("take",) * 16,
        )
    training.stopped_for_family_saturation = True

    assert runtime.training_progress_verdict(training) == (
        "experiment_stopped_during_training_for_family_saturation"
    )
    resources = runtime.training_resource_use(training)
    assert resources["completed_pairs"] == 256
    assert resources["training_environment_accesses"] == 512
    assert resources["candidate_optimizer_updates"] == 4
    assert resources["control_optimizer_updates"] == 4
    assert resources["canary_environment_accesses"] == 0
    assert resources["holdout_environment_accesses"] == 0

    environment_calls: list[int] = []
    with pytest.raises(runtime.SuccessorRuntimeError, match="cannot start"):
        runtime.run_bounded_paired_training(
            training,
            environment_factory=lambda seed: environment_calls.append(seed),
            remaining_seeds=tuple(range(256)),
            before_environment=lambda _arm, _seed: None,
            after_environment=lambda _arm, _seed: None,
            deadline=100.0,
            clock=lambda: 0.0,
        )
    assert environment_calls == []


def test_canary_concentration_requires_both_balanced_64_denominators():
    runtime = _runtime()
    balanced = tuple(
        _canary_pair(runtime, seed).candidate for seed in range(128)
    )

    passing = runtime.classify_canary_concentration(balanced)

    assert passing["passed"] is True
    for gate in ("selected_family", "unique_greedy_family"):
        assert passing[gate]["denominator"] == 128
        assert passing[gate]["family_count"] == 2
        assert passing[gate]["maximum_rate"] == 0.5

    concentrated = tuple(
        _canary_pair(
            runtime,
            seed,
            family="bowl" if seed < 122 else "take",
        ).candidate
        for seed in range(128)
    )
    failing = runtime.classify_canary_concentration(concentrated)
    assert failing["passed"] is False
    assert failing["selected_family"]["maximum_rate"] == 122 / 128
    assert failing["unique_greedy_family"]["maximum_rate"] == 122 / 128

    too_small = runtime.classify_canary_concentration(balanced[:63])
    assert too_small["passed"] is False
    assert too_small["selected_family"]["denominator"] == 63
    assert too_small["unique_greedy_family"]["denominator"] == 63


def test_family_only_shadow_adam_changes_only_clone_family_state():
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    optimizers = runtime.build_arm_optimizers(bootstrap)
    optimizers.candidate.zero_grad(set_to_none=True)
    warmup_loss = sum(
        parameter.square().sum()
        for parameter in optimizers.candidate.param_groups[0]["params"]
    )
    warmup_loss.backward()
    torch.nn.utils.clip_grad_norm_(
        optimizers.candidate.param_groups[0]["params"],
        1.0,
    )
    optimizers.candidate.step()
    rollout = runtime.rollout_arm_frozen_evaluation(
        bootstrap,
        arm="candidate",
        environment_factory=lambda seed: _RolloutEnvironment(
            seed,
            ("card_reward",),
        ),
        seed=43,
    )
    before_bootstrap = runtime.encode_paired_bootstrap(bootstrap)
    before_optimizer = runtime.encode_optimizer_state(optimizers.candidate)

    evidence = runtime.apply_family_only_shadow_step(
        bootstrap,
        candidate_optimizer=optimizers.candidate,
        decision=rollout.decisions[0],
    )

    assert runtime.encode_paired_bootstrap(bootstrap) == before_bootstrap
    assert runtime.encode_optimizer_state(optimizers.candidate) == before_optimizer
    assert evidence["advantage"] == 1.0
    assert evidence["gradient_reset_mode"] == "set_to_none=true"
    assert evidence["shadow_optimizer_steps"] == 1
    assert evidence["family_gradient_nonzero"] is True
    assert evidence["family_parameter_changed"] is True
    assert evidence["conditional_parameter_unchanged"] is True
    assert evidence["conditional_optimizer_state_unchanged"] is True
    assert evidence["conditional_output_unchanged"] is True
    assert evidence["postclip_global_norm"] <= 1.0 + 1e-6


def test_structural_canary_commits_first_outputs_before_exact_replay(
    monkeypatch,
):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    optimizers = runtime.build_arm_optimizers(bootstrap)
    seeds = tuple(range(2_000, 2_128))
    environment_calls = []
    rollout_calls = {seed: 0 for seed in seeds}
    commitments = []
    output_artifacts = {}

    def environment_factory(seed: int):
        environment_calls.append(seed)
        return object()

    def paired_rollout(_bootstrap, *, environment_factory, seed, **_kwargs):
        environment_factory(seed)
        environment_factory(seed)
        rollout_calls[seed] += 1
        return _canary_pair(runtime, seed)

    def publish(commitment, stored):
        assert len(environment_calls) == 4 * commitment["seed_index"] + 2
        assert "output" not in commitment
        binding = commitment["output_artifact"]
        assert binding["path"] not in output_artifacts
        assert hashlib.sha256(stored).hexdigest() == binding["stored_sha256"]
        uncompressed = gzip.decompress(stored)
        assert hashlib.sha256(uncompressed).hexdigest() == binding[
            "uncompressed_sha256"
        ]
        output_artifacts[binding["path"]] = stored
        commitments.append(copy.deepcopy(commitment))

    monkeypatch.setattr(
        runtime,
        "rollout_paired_frozen_evaluation",
        paired_rollout,
    )
    monkeypatch.setattr(
        runtime,
        "apply_family_only_shadow_step",
        lambda *_args, **_kwargs: {
            "family_parameter_changed": True,
            "shadow_optimizer_steps": 1,
        },
    )

    result = runtime.run_structural_canary(
        bootstrap,
        candidate_optimizer=optimizers.candidate,
        environment_factory=environment_factory,
        seeds=seeds,
        arm_bindings=_canary_arm_bindings(),
        publish_commitment=publish,
    )

    assert result.verdict == "canary_passed"
    assert result.resource_use == {
        "canary_environment_accesses": 512,
        "shadow_optimizer_steps": 1,
    }
    assert len(result.commitments) == 256
    assert tuple(commitments) == result.commitments
    assert len(result.replays) == 256
    assert len(output_artifacts) == 256
    assert all(count == 2 for count in rollout_calls.values())
    assert environment_calls == [seed for seed in seeds for _ in range(4)]
    for index, commitment in enumerate(commitments):
        assert commitment["sequence_index"] == index
        assert commitment["seed_index"] == index // 2
        assert commitment["arm"] == ("candidate" if index % 2 == 0 else "control")
        expected_previous = "0" * 64 if index == 0 else commitments[index - 1][
            "commitment_sha256"
        ]
        assert commitment["previous_commitment_sha256"] == expected_previous
        body = {
            key: value
            for key, value in commitment.items()
            if key != "commitment_sha256"
        }
        assert commitment["commitment_sha256"] == runtime.canonical_runtime_sha256(
            body
        )
        replay = result.replays[index]
        assert replay["sequence_index"] == index
        assert replay["first_commitment_sha256"] == commitment[
            "commitment_sha256"
        ]
        assert replay["output_sha256"] == commitment["output_sha256"]
        replay_body = {
            key: value for key, value in replay.items() if key != "replay_sha256"
        }
        assert replay["replay_sha256"] == runtime.canonical_runtime_sha256(
            replay_body
        )


def test_structural_canary_rejects_replay_drift_after_commitment(monkeypatch):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    optimizers = runtime.build_arm_optimizers(bootstrap)
    seeds = tuple(range(3_000, 3_128))
    calls = {seed: 0 for seed in seeds}
    published = []

    def paired_rollout(_bootstrap, *, seed, **_kwargs):
        calls[seed] += 1
        pair = _canary_pair(runtime, seed)
        if calls[seed] == 2:
            pair.candidate.final_snapshot["state"]["outcome"] = "player_victory"
        return pair

    monkeypatch.setattr(
        runtime,
        "rollout_paired_frozen_evaluation",
        paired_rollout,
    )

    with pytest.raises(runtime.SuccessorRuntimeError, match="replay"):
        runtime.run_structural_canary(
            bootstrap,
            candidate_optimizer=optimizers.candidate,
            environment_factory=lambda seed: object(),
            seeds=seeds,
            arm_bindings=_canary_arm_bindings(),
            publish_commitment=lambda commitment, _stored: published.append(
                commitment
            ),
        )
    assert [row["arm"] for row in published] == ["candidate", "control"]


def test_structural_canary_concentration_failure_skips_shadow(monkeypatch):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    optimizers = runtime.build_arm_optimizers(bootstrap)
    seeds = tuple(range(4_000, 4_128))
    commitments = []

    monkeypatch.setattr(
        runtime,
        "rollout_paired_frozen_evaluation",
        lambda _bootstrap, *, seed, **_kwargs: _canary_pair(
            runtime,
            seed,
            family="bowl",
        ),
    )
    monkeypatch.setattr(
        runtime,
        "apply_family_only_shadow_step",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("concentration failure reached shadow step")
        ),
    )

    result = runtime.run_structural_canary(
        bootstrap,
        candidate_optimizer=optimizers.candidate,
        environment_factory=lambda seed: object(),
        seeds=seeds,
        arm_bindings=_canary_arm_bindings(),
        publish_commitment=lambda commitment, _stored: commitments.append(
            commitment
        ),
    )

    assert result.verdict == "canary_failed_concentration"
    assert result.concentration["passed"] is False
    assert result.shadow_step is None
    assert result.resource_use == {
        "canary_environment_accesses": 512,
        "shadow_optimizer_steps": 0,
    }
    assert len(commitments) == 256


@pytest.mark.parametrize(
    "seeds",
    (
        tuple(range(127)),
        tuple(reversed(range(128))),
        tuple(range(127)) + (126,),
    ),
)
def test_structural_canary_rejects_nonexact_schedule_before_environment(seeds):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    optimizers = runtime.build_arm_optimizers(bootstrap)
    environment_calls = []

    with pytest.raises(runtime.SuccessorRuntimeError, match="128 ascending unique"):
        runtime.run_structural_canary(
            bootstrap,
            candidate_optimizer=optimizers.candidate,
            environment_factory=lambda seed: environment_calls.append(seed),
            seeds=seeds,
            arm_bindings=_canary_arm_bindings(),
            publish_commitment=lambda _commitment, _stored: None,
        )
    assert environment_calls == []


def test_holdout_bootstrap_uses_exact_seed_zero_draw_order_and_linear_quantiles():
    runtime = _runtime()
    differences = tuple((index - 255.5) / 256.0 for index in range(512))
    generator = random.Random(0)
    means = []
    for _ in range(10_000):
        total = 0.0
        for _ in range(512):
            total += differences[generator.randrange(512)]
        means.append(total / 512)
    means.sort()

    def quantile(probability: float) -> float:
        position = (10_000 - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        fraction = position - lower
        return means[lower] + fraction * (means[upper] - means[lower])

    interval = runtime.paired_floor_bootstrap_interval(differences)

    assert interval == {
        "bootstrap_seed": 0,
        "lower": quantile(0.025),
        "pair_count": 512,
        "quantile_method": "linear-position-(n-1)-p-v1",
        "resample_count": 10_000,
        "upper": quantile(0.975),
    }


@pytest.mark.parametrize(
    ("candidate", "control", "lower", "comparison", "floor_signal", "outcome"),
    (
        (2, 1, 0.1, "greater", True, "victory_and_floor_signal"),
        (1, 1, 0.1, "equal", True, "floor_only_signal"),
        (2, 1, 0.0, "greater", False, "inconclusive_signal"),
        (1, 2, 0.1, "fewer", True, "inconclusive_signal"),
        (1, 1, 0.0, "equal", False, "no_learning_signal"),
        (1, 2, -0.1, "fewer", False, "no_learning_signal"),
    ),
)
def test_holdout_outcome_truth_table_is_exhaustive_and_disjoint(
    candidate,
    control,
    lower,
    comparison,
    floor_signal,
    outcome,
):
    runtime = _runtime()
    result = runtime.classify_holdout_outcome(
        candidate_victories=candidate,
        control_victories=control,
        paired_floor_lower=lower,
    )
    assert result == {
        "candidate_victories": candidate,
        "control_victories": control,
        "floor_signal": floor_signal,
        "outcome_class": outcome,
        "paired_floor_lower": lower,
        "victory_comparison": comparison,
    }


def test_untouched_holdout_runs_each_arm_once_and_classifies_complete_evidence(
    monkeypatch,
):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    seeds = tuple(range(5_000, 5_512))
    environment_calls = []
    rollout_calls = []

    def environment_factory(seed: int):
        environment_calls.append(seed)
        return object()

    def paired_rollout(_bootstrap, *, environment_factory, seed, **_kwargs):
        environment_factory(seed)
        environment_factory(seed)
        rollout_calls.append(seed)
        return _holdout_pair(runtime, seed)

    monkeypatch.setattr(
        runtime,
        "rollout_paired_frozen_evaluation",
        paired_rollout,
    )
    before = runtime.encode_paired_bootstrap(bootstrap)

    result = runtime.run_untouched_holdout(
        bootstrap,
        environment_factory=environment_factory,
        seeds=seeds,
        arm_bindings=_canary_arm_bindings(),
        verified_canary=_verified_canary_binding(),
    )

    assert runtime.encode_paired_bootstrap(bootstrap) == before
    assert result.verdict == "holdout_completed"
    assert result.outcome_class == "victory_and_floor_signal"
    assert result.victory_counts == {"candidate": 512, "control": 0}
    assert result.bootstrap is not None
    assert result.bootstrap["lower"] > 0.0
    assert result.concentration["passed"] is True
    assert result.resource_use == {"holdout_environment_accesses": 1_024}
    assert len(result.pairs) == 512
    assert len(result.family_observations) == 512
    assert [row["seed"] for row in result.family_observations] == list(seeds)
    assert [row["seed"] for row in result.pairs] == list(seeds)
    assert all(row["floor_progress_difference"] == 1.0 for row in result.pairs)
    assert rollout_calls == list(seeds)
    assert environment_calls == [seed for seed in seeds for _ in range(2)]


def test_untouched_holdout_separates_concentration_failure_from_outcome(monkeypatch):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    seeds = tuple(range(6_000, 6_512))
    monkeypatch.setattr(
        runtime,
        "rollout_paired_frozen_evaluation",
        lambda _bootstrap, *, seed, **_kwargs: _holdout_pair(
            runtime,
            seed,
            family="bowl",
        ),
    )

    result = runtime.run_untouched_holdout(
        bootstrap,
        environment_factory=lambda seed: object(),
        seeds=seeds,
        arm_bindings=_canary_arm_bindings(),
        verified_canary=_verified_canary_binding(),
    )

    assert result.verdict == "holdout_failed_concentration"
    assert result.outcome_class is None
    assert result.bootstrap is None
    assert result.concentration["passed"] is False
    assert result.resource_use == {"holdout_environment_accesses": 1_024}


@pytest.mark.parametrize(
    "verified_canary",
    (
        None,
        {
            "terminal_sha256": "6" * 64,
            "verdict": "canary_failed_concentration",
            "verified": True,
        },
        {
            "terminal_sha256": "6" * 64,
            "verdict": "canary_passed",
            "verified": False,
        },
    ),
)
def test_holdout_rejects_missing_or_failed_canary_before_environment(
    verified_canary,
):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    environment_calls = []
    with pytest.raises(runtime.SuccessorRuntimeError, match="canary"):
        runtime.run_untouched_holdout(
            bootstrap,
            environment_factory=lambda seed: environment_calls.append(seed),
            seeds=tuple(range(512)),
            arm_bindings=_canary_arm_bindings(),
            verified_canary=verified_canary,
        )
    assert environment_calls == []


@pytest.mark.parametrize(
    "seeds",
    (
        tuple(range(511)),
        tuple(reversed(range(512))),
        tuple(range(511)) + (510,),
    ),
)
def test_holdout_rejects_nonexact_schedule_before_environment(seeds):
    runtime = _runtime()
    bootstrap = runtime.build_matched_bootstrap()
    environment_calls = []
    with pytest.raises(runtime.SuccessorRuntimeError, match="512 ascending unique"):
        runtime.run_untouched_holdout(
            bootstrap,
            environment_factory=lambda seed: environment_calls.append(seed),
            seeds=seeds,
            arm_bindings=_canary_arm_bindings(),
            verified_canary=_verified_canary_binding(),
        )
    assert environment_calls == []
