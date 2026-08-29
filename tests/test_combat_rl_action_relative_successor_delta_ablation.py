from __future__ import annotations

import copy
from collections import Counter

import pytest
import torch

from analysis_scripts import combat_rl_action_relative_successor_delta_ablation as ablation
from spirecomm.ai.rl.v2.action_relative_selective_classifier import (
    ActionRelativeSelectiveClassifier,
    ActionRelativeSelectiveConfig,
)
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256
from spirecomm.ai.rl.v2.network import create_dqn_v2
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2


def _state(value: float, *, action_dim: int = 6) -> dict[str, torch.Tensor]:
    return {
        "continuous": torch.tensor([value, value + 1], dtype=torch.float32),
        "card_ids": torch.tensor([1, 0], dtype=torch.long),
        "potion_ids": torch.tensor([0], dtype=torch.long),
        "relic_ids": torch.tensor([1], dtype=torch.long),
        "action_masks": torch.tensor(
            [True, True, True, False, False, False], dtype=torch.bool
        )[:action_dim],
    }


def _corpus(partition: str = "fit") -> dict:
    source = _state(1.0)
    tensors = {
        "continuous": torch.stack((source["continuous"], source["continuous"] + 2)),
        "card_ids": torch.stack((source["card_ids"], source["card_ids"])),
        "potion_ids": torch.stack((source["potion_ids"], source["potion_ids"])),
        "relic_ids": torch.stack((source["relic_ids"], source["relic_ids"])),
        "action_masks": torch.stack((source["action_masks"], source["action_masks"])),
        "guard_actions": torch.tensor([0, 0]),
        "target_actions": torch.tensor([2, 1]),
        "advantages": torch.tensor([1.0, 0.0]),
        "positive": torch.tensor([True, False]),
    }
    pairs = {
        "source_rows": torch.tensor([0, 0, 1, 1]),
        "candidate_actions": torch.tensor([1, 2, 1, 2]),
        "guard_returns": torch.tensor([0.0, 0.0, 1.0, 1.0]),
        "candidate_returns": torch.tensor([-1.0, 1.0, 1.0, 1.25]),
        "advantages": torch.tensor([-1.0, 1.0, 0.0, 0.25]),
        "guard_immediate_rewards": torch.tensor([0.0, 0.0, 0.5, 0.5]),
        "candidate_immediate_rewards": torch.tensor([-0.5, 0.75, 0.5, 0.75]),
        "guard_dispositions": torch.tensor(
            [ablation.SUPPORTED, ablation.SUPPORTED, ablation.TERMINAL_VICTORY,
             ablation.TERMINAL_VICTORY]
        ),
        "candidate_dispositions": torch.tensor(
            [ablation.SUPPORTED, ablation.TERMINAL_DEFEAT, ablation.SUPPORTED,
             ablation.TERMINAL_OTHER]
        ),
    }
    for prefix, values in (
        ("guard", [2.0, 2.0, 0.0, 0.0]),
        ("candidate", [3.0, 0.0, 4.0, 0.0]),
    ):
        pairs[f"{prefix}_successor_continuous"] = torch.stack(
            [_state(value)["continuous"] if value else torch.zeros(2) for value in values]
        )
        pairs[f"{prefix}_successor_card_ids"] = torch.stack(
            [_state(value)["card_ids"] if value else torch.zeros(2, dtype=torch.long)
             for value in values]
        )
        pairs[f"{prefix}_successor_potion_ids"] = torch.stack(
            [_state(value)["potion_ids"] if value else torch.zeros(1, dtype=torch.long)
             for value in values]
        )
        pairs[f"{prefix}_successor_relic_ids"] = torch.stack(
            [_state(value)["relic_ids"] if value else torch.zeros(1, dtype=torch.long)
             for value in values]
        )
        pairs[f"{prefix}_successor_action_masks"] = torch.stack(
            [_state(value)["action_masks"] if value else torch.zeros(6, dtype=torch.bool)
             for value in values]
        )
    return {
        "schema_version": ablation.CORPUS_SCHEMA,
        "corpus_kind": ablation.CORPUS_KIND,
        "partition": partition,
        "tensors": tensors,
        "metadata": [
            {
                "seed": 275000,
                "floor": 5,
                "guard_action_index": 0,
                "target_action_index": 2,
                "branch_returns": {"0": 0.0, "1": -1.0, "2": 1.0},
            },
            {
                "seed": 275001,
                "floor": 10,
                "guard_action_index": 0,
                "target_action_index": 2,
                "branch_returns": {"0": 1.0, "1": 1.0, "2": 1.25},
            },
        ],
        "pairs": pairs,
        "row_count": 2,
        "pair_count": 4,
    }


class _Environment:
    def __init__(self, transitions: dict[tuple[int, str], int], *, state: int = 0):
        self.transitions = transitions
        self.state = state

    def clone(self):
        return copy.deepcopy(self)

    def snapshot(self):
        return {"reward": float(self.state)}

    def step(self, action_id: str):
        self.state = self.transitions[(self.state, action_id)]

    def status(self):
        if self.state == -1:
            return {
                "terminal": False,
                "supported": False,
                "unsupported_reason": "unsupported_test_branch",
                "outcome": "undecided",
            }
        return {
            "terminal": self.state >= 3,
            "supported": True,
            "unsupported_reason": "",
            "outcome": "player_victory" if self.state >= 3 else "undecided",
        }


def _action(index: int) -> dict:
    return {
        "action_id": f"action:{index}",
        "kind": "play_card",
        "rl_action_index": index,
    }


def test_branch_capture_retains_first_successor_reward_and_identity() -> None:
    result = ablation.rollout_successor_branch(
        _Environment({(0, "action:1"): 1, (1, "action:2"): 3}),
        _action(1),
        source_actions_since_end_turn=0,
        continuation_selector=lambda _environment, _count: _action(2),
        continuation_decisions=1,
        discount=0.5,
        reward_fn=lambda _before, after, **_kwargs: {"total": after["reward"]},
        map_successor=lambda environment: _state(float(environment.state)),
    )
    assert result.complete is True
    assert result.total_return == pytest.approx(1.0 + 0.5 * 3.0)
    assert result.immediate_reward == pytest.approx(1.0)
    assert result.disposition == ablation.SUPPORTED
    assert torch.equal(result.successor["continuous"], torch.tensor([1.0, 2.0]))


def test_terminal_and_excluded_first_successors_are_explicit() -> None:
    terminal = ablation.rollout_successor_branch(
        _Environment({(0, "action:1"): 3}),
        _action(1),
        source_actions_since_end_turn=0,
        continuation_selector=lambda _environment, _count: _action(2),
        continuation_decisions=1,
        discount=0.99,
        reward_fn=lambda _before, after, **_kwargs: {"total": after["reward"]},
        map_successor=lambda _environment: pytest.fail("terminal state was mapped"),
    )
    assert terminal.complete is True
    assert terminal.successor is None
    assert terminal.disposition == ablation.TERMINAL_VICTORY

    excluded = ablation.rollout_successor_branch(
        _Environment({(0, "action:1"): -1}),
        _action(1),
        source_actions_since_end_turn=0,
        continuation_selector=lambda _environment, _count: _action(2),
        continuation_decisions=1,
        discount=0.99,
        reward_fn=lambda _before, after, **_kwargs: {"total": after["reward"]},
        map_successor=lambda _environment: pytest.fail("excluded state was mapped"),
    )
    assert excluded.complete is False
    assert excluded.exclusion_reason == "unsupported_test_branch"


def test_corpus_validation_enforces_pair_alignment_and_terminal_encoding() -> None:
    validated = ablation.validate_successor_corpus(_corpus(), expected_partition="fit")
    assert validated["row_count"] == 2
    assert validated["pair_count"] == 4
    assert validated["pairs"]["source_rows"].tolist() == [0, 0, 1, 1]

    bad_branch = _corpus()
    bad_branch["pairs"]["candidate_returns"][0] = 99.0
    with pytest.raises(ValueError, match="branch return"):
        ablation.validate_successor_corpus(bad_branch, expected_partition="fit")

    bad_terminal = _corpus()
    bad_terminal["pairs"]["candidate_successor_continuous"][1, 0] = 1.0
    with pytest.raises(ValueError, match="terminal successor"):
        ablation.validate_successor_corpus(bad_terminal, expected_partition="fit")


def test_corpus_validation_accepts_consistent_float32_return_rounding() -> None:
    corpus = _corpus()
    corpus["metadata"][0]["branch_returns"]["0"] = 1000.0
    corpus["metadata"][0]["branch_returns"]["1"] = 1000.1
    corpus["metadata"][0]["branch_returns"]["2"] = 1001.0
    corpus["pairs"]["guard_returns"][:2] = 1000.0
    corpus["pairs"]["candidate_returns"][0] = 1000.1
    corpus["pairs"]["candidate_returns"][1] = 1001.0
    corpus["pairs"]["advantages"][0] = 0.1
    corpus["pairs"]["advantages"][1] = 1.0
    validated = ablation.validate_successor_corpus(corpus, expected_partition="fit")
    assert validated["pairs"]["advantages"][0].item() == pytest.approx(0.1)


def test_corpus_identity_is_deterministic_and_sensitive_to_pair_bytes() -> None:
    first = ablation.successor_corpus_identity(_corpus())
    second = ablation.successor_corpus_identity(copy.deepcopy(_corpus()))
    assert first == second

    changed = _corpus()
    changed["pairs"]["candidate_immediate_rewards"][0] += 0.25
    observed = ablation.successor_corpus_identity(changed)
    assert observed["source_tensor_sha256"] == first["source_tensor_sha256"]
    assert observed["pair_tensor_sha256"] != first["pair_tensor_sha256"]


def test_partition_summary_is_complete_and_candidate_end_turn_is_rejected() -> None:
    corpus = ablation.validate_successor_corpus(_corpus(), expected_partition="fit")
    summary = ablation._partition_summary(
        corpus,
        registered_profiles=4,
        initialized_profiles=3,
        source_decisions=12,
        skip_reasons=Counter({"parent_not_end_turn": 2}),
        exclusion_reasons=Counter(),
        initialization_failures=Counter(),
    )
    assert summary["retained_state_count"] == 2
    assert summary["pair_count"] == 4
    assert summary["identity"] == ablation.successor_corpus_identity(corpus)

    bad = _corpus()
    bad["pairs"]["candidate_actions"][0] = 90
    with pytest.raises(ValueError, match="unsupported"):
        ablation.validate_successor_corpus(bad, expected_partition="fit")


def test_partition_contract_is_fixed_disjoint_and_rejects_smoke_rows() -> None:
    assert ablation.FIXED_COHORT["fit"] == [275000, 275767]
    assert ablation.FIXED_COHORT["calibration"] == [275768, 276023]
    assert ablation.FIXED_COHORT["fresh"] == [277000, 277255]
    ablation.validate_partition_seed_contract(
        {
            "fit": [{"seed": 275000}],
            "calibration": [{"seed": 275768}],
            "fresh": [{"seed": 277000}],
        }
    )
    with pytest.raises(ValueError, match="outside registered partition"):
        ablation.validate_partition_seed_contract(
            {
                "fit": [{"seed": 274999}],
                "calibration": [{"seed": 275768}],
                "fresh": [{"seed": 277000}],
            }
        )


def test_successor_delta_features_add_only_registered_causal_inputs() -> None:
    base = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    candidate_latent = torch.tensor([[5.0, 7.0], [11.0, 13.0]])
    guard_latent = torch.tensor([[2.0, 3.0], [17.0, 19.0]])
    features = ablation.compose_successor_delta_features(
        base,
        candidate_latent=candidate_latent,
        guard_latent=guard_latent,
        candidate_rewards=torch.tensor([2.0, -1.0]),
        guard_rewards=torch.tensor([0.5, 3.0]),
        candidate_dispositions=torch.tensor(
            [ablation.SUPPORTED, ablation.TERMINAL_DEFEAT]
        ),
        guard_dispositions=torch.tensor(
            [ablation.TERMINAL_VICTORY, ablation.SUPPORTED]
        ),
    )
    assert features[:, :2].equal(base)
    assert features[:, 2:4].tolist() == [[3.0, 4.0], [-6.0, -6.0]]
    assert features[:, 4].tolist() == pytest.approx([1.5, -4.0])
    assert features.shape[1] == 2 + 2 + 1 + 2 * ablation.DISPOSITION_COUNT


def test_real_v2_item_semantic_features_add_only_successor_delta_width() -> None:
    corpus = _corpus()
    source_count = corpus["row_count"]
    pair_count = corpus["pair_count"]
    corpus["tensors"]["continuous"] = torch.zeros(
        (source_count, StateEncoderV2.CONTINUOUS_DIM)
    )
    corpus["tensors"]["card_ids"] = torch.ones(
        (source_count, StateEncoderV2.CARD_SLOTS), dtype=torch.long
    )
    corpus["tensors"]["potion_ids"] = torch.zeros(
        (source_count, StateEncoderV2.POTION_SLOTS), dtype=torch.long
    )
    corpus["tensors"]["relic_ids"] = torch.ones(
        (source_count, StateEncoderV2.RELIC_SLOTS), dtype=torch.long
    )
    corpus["tensors"]["action_masks"] = torch.zeros(
        (source_count, 91), dtype=torch.bool
    )
    corpus["tensors"]["action_masks"][:, :3] = True
    for prefix in ("guard", "candidate"):
        corpus["pairs"][f"{prefix}_successor_continuous"] = torch.zeros(
            (pair_count, StateEncoderV2.CONTINUOUS_DIM)
        )
        corpus["pairs"][f"{prefix}_successor_card_ids"] = torch.zeros(
            (pair_count, StateEncoderV2.CARD_SLOTS), dtype=torch.long
        )
        corpus["pairs"][f"{prefix}_successor_potion_ids"] = torch.zeros(
            (pair_count, StateEncoderV2.POTION_SLOTS), dtype=torch.long
        )
        corpus["pairs"][f"{prefix}_successor_relic_ids"] = torch.zeros(
            (pair_count, StateEncoderV2.RELIC_SLOTS), dtype=torch.long
        )
        corpus["pairs"][f"{prefix}_successor_action_masks"] = torch.zeros(
            (pair_count, 91), dtype=torch.bool
        )
        supported = corpus["pairs"][f"{prefix}_dispositions"].eq(ablation.SUPPORTED)
        corpus["pairs"][f"{prefix}_successor_action_masks"][supported, 0] = True
    corpus = ablation.validate_successor_corpus(corpus, expected_partition="fit")

    metadata = {
        "network_type": "standard",
        "continuous_dim": StateEncoderV2.CONTINUOUS_DIM,
        "action_dim": 91,
        "card_vocab": 5,
        "potion_vocab": 4,
        "relic_vocab": 3,
        "card_slots": StateEncoderV2.CARD_SLOTS,
        "potion_slots": StateEncoderV2.POTION_SLOTS,
        "relic_slots": StateEncoderV2.RELIC_SLOTS,
    }
    torch.manual_seed(29)
    parent = create_dqn_v2(device="cpu", **metadata)
    extractor = ActionRelativeSelectiveClassifier(
        parent,
        metadata,
        ActionRelativeSelectiveConfig(hidden_dim=8, include_item_semantics=True),
        selection_threshold=0.0,
    )
    parent_before = state_dict_sha256(parent.state_dict())
    matrices = ablation.build_ablation_feature_matrices(extractor, corpus)
    assert matrices["control"].shape[0] == pair_count
    assert matrices["successor"].shape[1] == (
        matrices["control"].shape[1]
        + extractor.parent_latent_dim
        + 1
        + 2 * ablation.DISPOSITION_COUNT
    )
    assert state_dict_sha256(parent.state_dict()) == parent_before


def test_terminal_successor_latent_is_masked_before_delta() -> None:
    latent = torch.tensor([[2.0, 3.0], [4.0, 5.0]])
    masked = ablation.mask_terminal_latents(
        latent, torch.tensor([ablation.SUPPORTED, ablation.TERMINAL_VICTORY])
    )
    assert masked.tolist() == [[2.0, 3.0], [0.0, 0.0]]


def test_descriptive_signal_never_grants_hard_policy_authority() -> None:
    control = {
        "raw": {"selection": {"intervention_count": 100, "severe_harm_count": 20}},
        "weighted": {
            "intervention_precision": 0.40,
            "mean_selected_true_advantage": -0.10,
        },
    }
    successor = {
        "raw": {"selection": {"intervention_count": 80, "severe_harm_count": 8}},
        "weighted": {
            "intervention_precision": 0.51,
            "mean_selected_true_advantage": 0.01,
        },
    }
    signal = ablation.compare_representation_signal(control, successor)
    assert signal["all_conditions_passed"] is True
    assert signal["decision"] == "descriptive_successor_signal_without_policy_authority"
    assert signal["authority"]["fresh_lightspeed_gate"] is False

    successor["weighted"]["intervention_precision"] = 0.49
    assert ablation.compare_representation_signal(control, successor)[
        "all_conditions_passed"
    ] is False


def test_weighted_pair_plan_is_shared_and_deterministic() -> None:
    corpus = ablation.validate_successor_corpus(_corpus(), expected_partition="fit")
    weights = torch.tensor([0.75, 0.25], dtype=torch.float64)
    first = ablation._weighted_sampling_plan(corpus, weights)
    second = ablation._weighted_sampling_plan(corpus, weights)
    assert first["sha256"] == second["sha256"]
    assert torch.equal(first["class_plan"], second["class_plan"])
    assert torch.equal(first["ranking_plan"], second["ranking_plan"])
    assert first["labels"].tolist() == [0, 2, 1, 1]


class _IdentityHead(torch.nn.Module):
    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return values


def test_head_evaluation_selects_one_pair_per_source_and_preserves_raw_safety() -> None:
    corpus = _corpus(partition="fresh")
    logits = torch.tensor(
        [
            [2.0, 0.0, 0.0],
            [0.0, 0.0, 3.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 2.0],
        ]
    )
    result = ablation.evaluate_ablation_head(
        _IdentityHead(),
        logits,
        corpus,
        torch.tensor([0.8, 0.2], dtype=torch.float64),
        selection_threshold=0.0,
    )
    assert result["raw"]["selection"]["intervention_count"] == 2
    assert result["raw"]["selection"]["severe_harm_count"] == 0
    assert result["raw"]["selection"]["illegal_action_count"] == 0
    assert result["selection"]["actions"].tolist() == [2, 2]
    assert result["weighted"]["intervention_precision"] == pytest.approx(0.8)
    assert result["weighted"]["mean_selected_true_advantage"] == pytest.approx(0.85)


def test_registration_binds_recipe_inputs_and_development_authority() -> None:
    registration = ablation.build_corpus_registration(
        "a" * 40,
        experiment_id=ablation.CORPUS_EXPERIMENT_ID,
        output_dir=ablation.CORPUS_OUTPUT_DIR,
        smoke=False,
    )
    validated = ablation.validate_corpus_registration(registration, smoke=False)
    assert validated["experiment_id"].endswith("-r2")
    assert validated["attempt"] == 2
    assert validated["inputs"]["predecessor_failure"]["sha256"] == (
        "c841ecae533f9e85caefa89867ee74399d8c08ca68210a8a264521b117abc3dd"
    )
    assert validated["recipe"] == ablation.FIXED_CORPUS_RECIPE
    assert validated["authority"]["native_loading"] is True
    assert validated["authority"]["gameplay"] is False
    assert validated["authority"]["training"] is False

    registration["recipe"]["battle_indices"] = [0]
    with pytest.raises(ValueError, match="registration .* differs"):
        ablation.validate_corpus_registration(registration, smoke=False)


def test_fit_registration_binds_fresh_corpus_recipe_and_no_game_authority() -> None:
    names = {
        "items_json",
        "parent_checkpoint",
        "real_r14_replay",
        "real_r15_replay",
        "fit_corpus",
        "calibration_corpus",
        "fresh_corpus",
        "corpus_report",
        "corpus_manifest",
        "corpus_registration",
    }
    inputs = {
        name: {"path": f"D:/{name}.bin", "sha256": "b" * 64}
        for name in names
    }
    registration = ablation.build_fit_registration("a" * 40, inputs=inputs)
    validated = ablation.validate_fit_registration(registration)
    assert validated["recipe"] == ablation.FIXED_ABLATION_RECIPE
    assert validated["inputs"]["fresh_corpus"]["sha256"] == "b" * 64
    assert validated["authority"]["cpu_model_fitting"] is True
    assert validated["authority"]["gameplay"] is False

    registration["recipe"]["updates"] = 1
    with pytest.raises(ValueError, match="registration payload differs"):
        ablation.validate_fit_registration(registration)


def test_fresh_loader_is_rejected_until_both_arms_and_thresholds_are_frozen() -> None:
    boundary = ablation.FreshAccessBoundary()
    with pytest.raises(RuntimeError, match="both arms"):
        boundary.authorize_fresh_access()
    boundary.freeze_arm("control", "a" * 64, 1.0)
    with pytest.raises(RuntimeError, match="both arms"):
        boundary.authorize_fresh_access()
    boundary.freeze_arm("successor", "b" * 64, 2.0)
    receipt = boundary.authorize_fresh_access()
    assert receipt["loaded_after_both_arms_and_thresholds_frozen"] is True
    with pytest.raises(RuntimeError, match="only once"):
        boundary.authorize_fresh_access()
