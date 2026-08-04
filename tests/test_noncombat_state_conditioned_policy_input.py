from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest
import torch

from analysis_scripts.noncombat_policy_diagnostics import summarize_policy_diagnostics
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    TARGET_CATEGORIES,
)
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    FEATURE_VERSION,
    HASH_DIM,
    POLICY_INPUT_SCHEMA_VERSION,
    PROJECTION_VERSION,
    PolicyInputError,
    build_policy_diagnostic_row,
    policy_input_metadata,
    project_state_conditioned_policy_input,
)
from analysis_scripts.noncombat_state_conditioned_ranker import (
    ARCHITECTURE_ID,
    StateConditionedCandidateRanker,
)


ROOT = Path(__file__).resolve().parents[1]


def _snapshot(category: str = "shop") -> dict[str, object]:
    return {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_control": {
            "history": [{"category": "combat", "outcome": "ignored"}],
            "policy_id": "test-baseline-v1",
        },
        "category": category,
        "decision_count": 7,
        "schema_version": STATE_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "state": {
            "cur_hp": 55,
            "deck": [{"id": "Strike_R", "upgrades": 0}],
            "floor": 8,
            "gold": 123,
            "nested": {"outcome": "undecided", "seed": "hidden"},
        },
        "terminal": False,
    }


def _candidate(
    action_id: str,
    category: str = "shop",
    *,
    kind: str = "choose",
    price: int = 50,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "available": True,
        "category": category,
        "kind": kind,
        "label": action_id,
        "raw": {"price": price, "provenance": {"source": "hidden"}},
    }


def _two_candidates(category: str = "shop") -> list[dict[str, object]]:
    return [
        _candidate(f"{category}:choice:a", category, price=10),
        _candidate(f"{category}:choice:b", category, price=20),
    ]


@pytest.mark.parametrize("category", TARGET_CATEGORIES)
def test_exact_api_v3_projection_supports_every_target_category(category):
    result = project_state_conditioned_policy_input(
        _snapshot(category), _two_candidates(category)
    )

    assert result.state_features.shape == (HASH_DIM,)
    assert result.candidate_features.shape == (2, HASH_DIM)
    assert result.state_features.dtype == torch.float32
    assert result.candidate_features.dtype == torch.float32
    assert result.state_features.device.type == "cpu"
    assert result.candidate_features.device.type == "cpu"
    assert torch.isfinite(result.state_features).all().item()
    assert torch.isfinite(result.candidate_features).all().item()


def test_state_and_candidate_channels_change_independently_and_follow_permutation():
    low_state = _snapshot()
    high_state = copy.deepcopy(low_state)
    high_state["state"]["gold"] = 999
    candidates = _two_candidates()

    low = project_state_conditioned_policy_input(low_state, candidates)
    high = project_state_conditioned_policy_input(high_state, candidates)
    reordered = project_state_conditioned_policy_input(
        low_state, list(reversed(candidates))
    )

    assert not torch.equal(low.state_features, high.state_features)
    assert torch.equal(low.candidate_features, high.candidate_features)
    assert torch.equal(low.state_features, reordered.state_features)
    assert torch.equal(low.candidate_features[0], reordered.candidate_features[1])
    assert torch.equal(low.candidate_features[1], reordered.candidate_features[0])


def test_projection_is_repeatable_leakage_controlled_and_source_preserving():
    snapshot = _snapshot()
    candidates = _two_candidates()
    original_snapshot = copy.deepcopy(snapshot)
    original_candidates = copy.deepcopy(candidates)

    first = project_state_conditioned_policy_input(snapshot, candidates)
    second = project_state_conditioned_policy_input(snapshot, candidates)
    leaked_snapshot = copy.deepcopy(snapshot)
    leaked_snapshot["baseline_control"]["history"] = [
        {"reward": 100.0, "seed": "different"}
    ]
    leaked_snapshot["state"]["nested"] = {
        "outcome": "player_victory",
        "reward": 2.0,
        "seed": "different",
        "terminal_floor": 57,
    }
    leaked_candidates = copy.deepcopy(candidates)
    leaked_candidates[0]["raw"]["reward"] = 99.0
    leaked_candidates[0]["raw"]["target_action_id"] = candidates[0]["action_id"]
    leaked = project_state_conditioned_policy_input(
        leaked_snapshot, leaked_candidates
    )

    assert torch.equal(first.state_features, second.state_features)
    assert torch.equal(first.candidate_features, second.candidate_features)
    assert torch.equal(first.state_features, leaked.state_features)
    assert torch.equal(first.candidate_features, leaked.candidate_features)
    assert snapshot == original_snapshot
    assert candidates == original_candidates


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda snapshot, candidates: candidates.clear(), "nonempty"),
        (
            lambda snapshot, candidates: candidates.append(
                copy.deepcopy(candidates[0])
            ),
            "duplicate",
        ),
        (lambda snapshot, candidates: snapshot.__setitem__("terminal", True), "terminal"),
        (
            lambda snapshot, candidates: snapshot.__setitem__("category", "combat"),
            "category",
        ),
        (
            lambda snapshot, candidates: snapshot["state"].__setitem__(
                "gold", math.inf
            ),
            "finite",
        ),
        (
            lambda snapshot, candidates: candidates[0]["raw"].__setitem__(
                "price", math.nan
            ),
            "finite",
        ),
    ],
)
def test_projection_fails_closed_on_invalid_input(mutate, message):
    snapshot = _snapshot()
    candidates = _two_candidates()
    mutate(snapshot, candidates)

    with pytest.raises(PolicyInputError, match=message):
        project_state_conditioned_policy_input(snapshot, candidates)


def test_policy_input_metadata_is_stable_json_compatible_and_all_false():
    expected = {
        "architecture_id": ARCHITECTURE_ID,
        "authority": {
            "experiment_execution": False,
            "formal_rl": False,
            "gameplay": False,
            "model_loading": False,
            "native_loading": False,
            "policy_promotion": False,
            "qualification": False,
            "seed_access": False,
            "training": False,
        },
        "channel_composition": "separate_state_and_candidate",
        "device": "cpu",
        "dtype": "float32",
        "feature_version": FEATURE_VERSION,
        "hash_dim": HASH_DIM,
        "projection_version": PROJECTION_VERSION,
        "schema_version": POLICY_INPUT_SCHEMA_VERSION,
    }

    assert policy_input_metadata() == expected
    assert json.loads(json.dumps(expected, sort_keys=True)) == expected


def _matching_ranker(low, high) -> StateConditionedCandidateRanker:
    state_delta = high.state_features - low.state_features
    candidate_delta = low.candidate_features[1] - low.candidate_features[0]
    assert torch.dot(state_delta, state_delta).item() > 0.0
    assert torch.dot(candidate_delta, candidate_delta).item() > 0.0
    state_axis = state_delta / torch.dot(state_delta, state_delta)
    candidate_axis = candidate_delta / torch.dot(candidate_delta, candidate_delta)

    model = StateConditionedCandidateRanker(input_dim=HASH_DIM, hidden_dim=2)
    with torch.no_grad():
        model.hidden.weight.zero_()
        model.hidden.bias.zero_()
        model.hidden.weight[0, :HASH_DIM] = state_axis
        model.hidden.weight[0, HASH_DIM:] = -candidate_axis
        model.hidden.bias[0] = (
            -torch.dot(state_axis, low.state_features)
            + torch.dot(candidate_axis, low.candidate_features[0])
        )
        model.hidden.weight[1, :HASH_DIM] = -state_axis
        model.hidden.weight[1, HASH_DIM:] = candidate_axis
        model.hidden.bias[1] = (
            torch.dot(state_axis, low.state_features)
            - torch.dot(candidate_axis, low.candidate_features[0])
        )
        model.scorer.weight.copy_(torch.tensor([[-1.0, -1.0]]))
        model.scorer.bias.zero_()
    return model


def test_integrated_state_only_change_can_reverse_candidate_ordering():
    low_snapshot = _snapshot()
    high_snapshot = copy.deepcopy(low_snapshot)
    high_snapshot["state"]["gold"] = 999
    candidates = _two_candidates()
    low = project_state_conditioned_policy_input(low_snapshot, candidates)
    high = project_state_conditioned_policy_input(high_snapshot, candidates)
    model = _matching_ranker(low, high)

    low_scores = model(low.state_features, low.candidate_features)
    high_scores = model(high.state_features, high.candidate_features)
    reordered = project_state_conditioned_policy_input(
        low_snapshot, list(reversed(candidates))
    )

    assert int(torch.argmax(low_scores).item()) == 0
    assert int(torch.argmax(high_scores).item()) == 1
    assert torch.equal(
        model(reordered.state_features, reordered.candidate_features),
        low_scores.flip(0),
    )


def test_scored_decision_builds_a_canonical_summarizable_row():
    candidates = _two_candidates("card_reward")
    candidates[0]["kind"] = "take"
    candidates[1]["kind"] = "skip"
    row = build_policy_diagnostic_row(
        decision_id="episode-1:decision-7",
        snapshot=_snapshot("card_reward"),
        candidates=candidates,
        scores=torch.tensor([0.25, 0.75], dtype=torch.float32),
        selected_index=1,
    )

    assert row == {
        "candidate_scores": {
            candidates[0]["action_id"]: 0.25,
            candidates[1]["action_id"]: 0.75,
        },
        "candidates": [
            {"action_id": candidates[0]["action_id"], "kind": "take"},
            {"action_id": candidates[1]["action_id"], "kind": "skip"},
        ],
        "category": "card_reward",
        "decision_id": "episode-1:decision-7",
        "selected_action_id": candidates[1]["action_id"],
    }
    summary = summarize_policy_diagnostics([row])
    assert summary["decision_count"] == 1
    assert summary["categories"]["card_reward"]["selected_kinds"] == {
        "skip": {"count": 1, "rate": 1.0}
    }


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"decision_id": ""}, "decision_id"),
        ({"scores": torch.tensor([0.5])}, "score"),
        ({"scores": torch.tensor([0.5, math.nan])}, "finite"),
        ({"selected_index": -1}, "selected_index"),
        ({"selected_index": True}, "selected_index"),
    ],
)
def test_diagnostic_row_fails_closed_on_inconsistent_input(kwargs, message):
    arguments = {
        "decision_id": "episode-1:decision-7",
        "snapshot": _snapshot(),
        "candidates": _two_candidates(),
        "scores": torch.tensor([0.25, 0.75], dtype=torch.float32),
        "selected_index": 1,
    }
    arguments.update(kwargs)

    with pytest.raises(PolicyInputError, match=message):
        build_policy_diagnostic_row(**arguments)


def test_fresh_process_projection_does_not_import_native_or_gameplay_modules():
    script = """
import json
import sys

watched = {
    "sts_lightspeed_noncombat_adapter",
    "spirecomm.communication.action",
    "spirecomm.communication.coordinator",
    "spirecomm.ai.rl_agent",
    "scripts.run_training_batch",
    "main",
}
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION, SOURCE_TYPE, STATE_SCHEMA_VERSION
)
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    project_state_conditioned_policy_input,
)
snapshot = {
    "adapter_api_version": ADAPTER_API_VERSION,
    "baseline_control": {"history": [], "policy_id": "test"},
    "category": "shop",
    "decision_count": 0,
    "schema_version": STATE_SCHEMA_VERSION,
    "source_type": SOURCE_TYPE,
    "state": {"floor": 1, "gold": 99},
    "terminal": False,
}
candidates = [{
    "action_id": "shop:leave:0",
    "available": True,
    "category": "shop",
    "kind": "leave",
    "label": "Leave",
    "raw": {},
}]
project_state_conditioned_policy_input(snapshot, candidates)
print(json.dumps(sorted(watched & set(sys.modules))))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == []
